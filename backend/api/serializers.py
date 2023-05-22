from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.password_validation import validate_password
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from api.fields import Hex2NameColor
from recipes.models import (FavoriteRecipeUser, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCartUser, Tag)
from users.models import Follow, User


class UserSerializer(serializers.ModelSerializer):
    """Сериалайзер пользователя"""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'password',
        )
        extra_kwargs = {'password': {'write_only': True}}
        read_only_fields = 'is_subscribed',

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(
            user=user, following=obj
        ).exists()


class NewUserSerializer(serializers.ModelSerializer):
    """Сериалайзер для респонса при создании пользователя"""

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data: dict) -> User:
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class SetPasswordSerializer(serializers.Serializer):
    """Сериалайзер установки пароля."""
    new_password = serializers.CharField(max_length=150, required=True)
    current_password = serializers.CharField(max_length=150, required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class TagSerializer(serializers.ModelSerializer):
    color = Hex2NameColor()

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериалайзер ингредиента"""

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit'
        )


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер для связующей таблицы Рецепта с ингредиентом."""
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.StringRelatedField(source='ingredient.name')
    measurement_unit = serializers.StringRelatedField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount',
        )


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода id и количества ингредиента."""
    id = serializers.IntegerField(write_only=True)
    amount = serializers.IntegerField(write_only=True)

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер рецепта"""
    author = UserSerializer(read_only=True)
    image = Base64ImageField()
    ingredients = IngredientRecipeSerializer(
        read_only=True,
        many=True,
        source='ingredient_in_recipe'
    )
    tags = TagSerializer(many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
        'is_favorited', 'is_in_shopping_cart', 'name',
        'image', 'text', 'cooking_time',)

    def get_is_favorited(self, obj):
        """Проверка, находится ли в избранном."""
        user = self.context['request'].user
        # Если пользователь не аноним и подписка существует
        if (user != AnonymousUser()
                and FavoriteRecipeUser.objects.filter(
                    user=user, recipe=obj.pk).exists()):
            return True
        return False

    # def get_is_favorited(self, obj):
    #     user = self.context['request'].user.id
    #     recipe = obj.id
    #     return FavoriteRecipeUser.objects.filter(
    #         user_id=user,
    #         recipe_id=recipe
    #     ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user.id
        recipe = obj.id
        return ShoppingCartUser.objects.filter(
            user_id=user,
            recipe_id=recipe
        ).exists()


class RecipePostSerializer(serializers.ModelSerializer):
    """Сериалайзер для создания рецепта"""
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    ingredients = IngredientAmountSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Необходимо выбрать ингредиенты!'
            )
        for ingredient in ingredients:
            if ingredient['amount'] < 1:
                raise serializers.ValidationError(
                    'Количество не может быть меньше 1!'
                )

        ids = [ingredient['id'] for ingredient in ingredients]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                'Данный ингредиент уже есть в рецепте!'
            )
        return ingredients

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError(
                'Необходимо выбрать теги!'
            )
        return tags

    def add_ingredients_and_tags(self, tags, ingredients, recipe):
        for tag in tags:
            recipe.tags.add(tag)
            recipe.save()
        for ingredient in ingredients:
            IngredientRecipe.objects.create(
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'),
                recipe=recipe
            )
        return recipe

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        return self.add_ingredients_and_tags(
            tags, ingredients, recipe
        )

    def update(self, instance, validated_data):
        instance.ingredients.clear()
        instance.tags.clear()
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        return self.add_ingredients_and_tags(
            tags, ingredients, instance
        )

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class SubscribeRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер для подписки на пользователя"""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time',)


class SubscriptionsSerializer(serializers.ModelSerializer):
    """Сериалайзер для вывода подписок пользователя."""

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_is_subscribed(self, obj):
        """Подписан ли текущий пользователь на другого пользователя."""
        return user_is_subscribed(self, obj)

    def get_recipes_count(self, obj):
        """Общее количество рецептов пользователя."""
        return Recipe.objects.filter(author=obj).count()

    def get_recipes(self, obj):
        """Получить рецепты пользователя."""
        recipes_limit = self.context['request'].GET.get('recipes_limit')
        interes_user = obj
        if recipes_limit:
            return SubRecipeSerializer(
                Recipe.objects.filter(
                    author=interes_user
                )[:int(recipes_limit)],
                many=True
            ).data
        return SubRecipeSerializer(
            Recipe.objects.filter(author=interes_user),
            many=True
        ).data


def user_is_subscribed(self, obj):
    """Подписан ли текущий пользователь на другого пользователя."""
    user = self.context['request'].user
    if user.is_anonymous:
        return False
    return Follow.objects.filter(user=user, following=obj.pk).exists()


class SubRecipeSerializer(serializers.ModelSerializer):
    """Сериалайзер для вывода полей рецепта в подписках."""

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )
