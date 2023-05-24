from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from api.serializers import SubscribeRecipeSerializer
from recipes.models import Recipe


def post_delete_relationship_user_with_object(request, pk, model, message):
    """Добавление и удаление рецепта в связующей таблице для пользователя."""
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
        text = SubscribeRecipeSerializer(recipe)
        text = text.data
        return Response(text, status=status.HTTP_201_CREATED)
    obj_recipe = model.objects.filter(
        recipe=recipe,
        user=request.user
    )
    if obj_recipe.exists():
        obj_recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(
        {'errors': f'Рецепта с номером {pk} нет у Вас в {message}.'},
        status=status.HTTP_400_BAD_REQUEST
    )
