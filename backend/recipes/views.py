from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import CustomRecipeFilterSet, IngredientFilter
from api.pagination import CustomPagination
from api.permissions import IsAdminOrOwnerOrReadOnly
from api.serializers import (IngredientSerializer, RecipePostSerializer,
                             RecipeSerializer, TagSerializer)
from recipes.models import (FavoriteRecipeUser, Ingredient, Recipe,
                            ShoppingCartUser, Tag)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = IsAdminOrOwnerOrReadOnly,
    serializer_class = RecipeSerializer
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = CustomRecipeFilterSet

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeSerializer
        return RecipePostSerializer

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        """Эндпоинт для избранных рецептов."""
        return post_delete_relationship_user_with_object(
            request=request,
            pk=pk,
            model=FavoriteRecipeUser,
            message='избранном'
        )

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        """Эндпоинт для списка покупок."""
        return post_delete_relationship_user_with_object(
            request=request,
            pk=pk,
            model=ShoppingCartUser,
            message='списке покупок'
        )

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        """Эндпоинт для загрузки списка покупок."""
        recipes_user_in_shoplist = ShoppingCartUser.objects.filter(
            user=request.user
        )
        recipes = Recipe.objects.filter(
            recipe_in_shoplist__in=recipes_user_in_shoplist
        )
        ingredients = Ingredient.objects.filter(
            ingredient_in_recipe__recipe__in=recipes
        )
        queryset_ingredients = ingredients.annotate(
            sum_amount_ingredients=(Sum('ingredient_in_recipe__amount'))
        )
        content = (
                'Ваш сервис, Продуктовый помощник, подготовил \nсписок '
                + 'покупок по выбранным рецептам:\n'
                + 50 * '_'
                + '\n\n'
        )
        if not queryset_ingredients:
            content += (
                    'К сожалению, в списке ваших покупок пусто - '
                    + 'поскольку Вы не добавили в него ни одного рецепта.'
            )
        else:
            for ingr in queryset_ingredients:
                content += (
                        f'\t•\t{ingr.name} ({ingr.measurement_unit}) — '
                        + f'{ingr.sum_amount_ingredients}\n\n'
                )
        filename = 'my_shopping_cart.txt'
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename={0}'.format(
            filename
        )
        return response


class TagViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с тэгами"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с ингредиентами"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = IngredientFilter


def post_delete_relationship_user_with_object(request, pk, model, message):
    """Добавление и удаление рецепта в связующей таблице для пользователя."""
    # получаем рецепт по первичному ключу id
    recipe = get_object_or_404(Recipe, id=pk)
    if request.method == 'POST':
        if model.objects.filter(
                recipe=recipe,
                user=request.user
        ).exists():
            return Response(
                {'errors': f'Рецепт с номером {pk} уже у Вас в {message}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        model.objects.create(
            recipe=recipe,
            user=request.user
        )
        text = {
            'id': recipe.id,
            'name': recipe.name,
            'image': str(recipe.image),
            'cooking_time': recipe.cooking_time
        }
        return Response(text, status=status.HTTP_201_CREATED)
    obj_recipe = model.objects.filter(
        recipe=recipe,
        user=request.user
    )
    if obj_recipe:
        obj_recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(
        {'errors': f'Рецепта с номером {pk} нет у Вас в {message}.'},
        status=status.HTTP_400_BAD_REQUEST
    )
