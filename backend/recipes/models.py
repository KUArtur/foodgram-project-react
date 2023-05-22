from colorfield.fields import ColorField
from django.core.validators import MinValueValidator
from django.db import models

from recipes.validators import hex_field_validator, slug_field_validator
from users.models import User


class Ingredient(models.Model):
    """Модель избранных ингредиента"""
    name = models.CharField(
        db_index=True,
        max_length=200,
        verbose_name='Название',
        help_text='Название ингредиента',
    )
    measurement_unit = models.CharField(
        default='г',
        max_length=200,
        verbose_name='Единицы измерения',
        help_text='Единицы измерения',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self) -> str:
        return f'{self.name} ({self.measurement_unit})'


class Tag(models.Model):
    name = models.CharField(
        unique=True,
        db_index=True,
        max_length=200,
        verbose_name='Тег',
        help_text='Введите название тега',
    )
    color = ColorField(
        format='hex',
        default='#FF0000',
        max_length=7,
        verbose_name='Цветовой HEX-код',
        help_text='Цветовой HEX-код',
        validators=[hex_field_validator]
    )

    slug = models.SlugField(
        unique=True,
        db_index=True,
        max_length=200,
        verbose_name='Слаг тега',
        help_text='Введите слаг тега',
        validators=[slug_field_validator]
    )

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'
        ordering = ('name',)

    def __str__(self) -> str:
        return (f'{self.name}'
                f'(цвет: {self.color})')


class Recipe(models.Model):
    """Модель рецепта"""
    name = models.CharField(
        max_length=200,
        verbose_name='Название блюда',
        db_index=True,
        help_text='Введите название блюда',
    )
    text = models.TextField(max_length=500, verbose_name='Описание блюда')
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления (мин)',
        default=0,
        validators=[MinValueValidator(1)]
    )

    image = models.ImageField(verbose_name='Изображение блюда')
    author = models.ForeignKey(
        verbose_name='Автор рецепта',
        related_name='recipes',
        to=User,
        on_delete=models.CASCADE,
    )
    tags = models.ManyToManyField(Tag, through='TagRecipe')
    ingredients = models.ManyToManyField(
        Ingredient,
        db_index=True,
        through='IngredientRecipe',
        verbose_name='Список ингредиентов',
        help_text='Ингредиенты для приготовления блюда',
        related_name='ingredients_recipes',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания рецепта',
    )

    class Meta:
        verbose_name = 'Блюдо'
        verbose_name_plural = 'Блюда'
        ordering = ('name',)

    def __str__(self) -> str:
        return self.name


class TagRecipe(models.Model):
    """Модель тэга"""
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='recipe_tags',
        verbose_name='Тег'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_tags',
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Связь тэга c рецептом'
        verbose_name_plural = 'Связи тэга c рецептами'
        constraints = [
            models.UniqueConstraint(
                name='unique_tag_recipe',
                fields=['tag', 'recipe'],
            ),
        ]

    def __str__(self):
        return f'{self.tag} {self.recipe}'


class IngredientRecipe(models.Model):
    """Модель отношения Ингредиент-Рецепт."""
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_in_recipe',
        verbose_name='Ингридиент',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_in_recipe',
        verbose_name='Рецепт',
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество ингредиента в рецепте',
        validators=[
            MinValueValidator(
                limit_value=1,
                message='Количество должно быть больше 0.'
            )
        ],
    )

    class Meta:
        verbose_name = 'Связь ингредиента c рецептом'
        verbose_name_plural = 'Связи ингредиентов c рецептами'
        constraints = [
            models.UniqueConstraint(
                name='unique_ingredient_recipe',
                fields=['ingredient', 'recipe'],
            ),
        ]

    def __str__(self):
        return 'Ингридиент {} в рецепте {}'.format(
            self.ingredient,
            self.recipe
        )


class ShoppingCartUser(models.Model):
    """Модель корзины покупок (отношение рецепт-пользователь)"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipe_in_shoplist',
        verbose_name='Пользователь, имеющий рецепт в cписке покупок',
        help_text='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_in_shoplist',
        verbose_name='Рецепт из списка покупок пользователя',
        help_text='Рецепт в списке покупок', )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                name='unique_user_shoplist',
                fields=['user', 'recipe'],
            ),
        ]

    def __str__(self):
        return 'У {} в списке покупок рецепт: {}'.format(
            self.user,
            self.recipe
        )


class FavoriteRecipeUser(models.Model):
    """Модель избранных рецептов"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_recipes',
        verbose_name='Пользователь, имеющий избранные рецепты',
        help_text='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorite_recipes',
        verbose_name='Избранный рецепт определенного пользователя',
        help_text='Избранный рецепт',
    )

    class Meta:
        verbose_name = 'Список избранного'
        verbose_name_plural = 'Списки избранного'
        constraints = [
            models.UniqueConstraint(
                name='unique_favorite_recipe_user',
                fields=['user', 'recipe'],
            ),
        ]

    def __str__(self):
        return 'У {} в избранном рецепт: {}'.format(
            self.user,
            self.recipe
        )
