from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.filters import CustomRecipeFilterSet, IngredientFilter
from api.pagination import CustomPagination
from api.permissions import IsAdminOrOwnerOrReadOnly
from api.serializers import (IngredientSerializer, NewUserSerializer,
                             RecipePostSerializer, RecipeSerializer,
                             SetPasswordSerializer, SubscriptionsSerializer,
                             TagSerializer, UserSerializer)
from api.utils import post_delete_relationship_user_with_object
from recipes.models import (FavoriteRecipeUser, Ingredient, Recipe,
                            ShoppingCartUser, Tag)
from users.models import Follow, User


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

    @action(detail=True, methods=['post', 'delete', 'get'])
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


class UserViewSet(viewsets.ModelViewSet):
    """
    Набор представлений для работы с пользователями.
    """
    queryset = User.objects.all()
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return NewUserSerializer
        return UserSerializer

    @action(
        detail=False, methods=('get', 'patch', 'post',),
        url_path='me', url_name='me',
        permission_classes=[permissions.IsAuthenticated]
    )
    def get_user_me(self, request):
        """Метод обрабатывающий эндпоинт me."""
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def set_password(self, request):
        """Метод обрабатывающий эндпоинт set_password."""
        user = get_object_or_404(User, email=request.user.email)
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if check_password(request.data['current_password'], user.password):
            new_password = make_password(request.data['new_password'])
            user.password = new_password
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
                {
                    'current_password':
                        'Введенный и текущий пароли не совпадают'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        methods=['GET'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        """
        Метод обрабатывающий эндпоинт subscriptions.
        Возвращает пользователей, на которых подписан текущий пользователь.
        В выдачу добавляются рецепты.
        """
        user = request.user
        queryset = User.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscriptionsSerializer(
            data=pages,
            many=True,
            context={
                'request': request
            },
        )
        return self.get_paginated_response(data=serializer.data)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
    )
    def subscribe(self, request, pk=None):
        """Метод обрабатывающий эндпоинт subscribe."""
        # получаем интересующего пользователя из url
        interest_user = get_object_or_404(User, id=pk)
        if request.method == 'POST':
            if request.user == interest_user:
                return Response(
                    {'errors': 'Невозможно подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif Follow.objects.filter(
                    following=interest_user,
                    user=request.user
            ).exists():
                return Response(
                    {'errors': (
                            'Вы уже подписаны на пользователя '
                            + f'{interest_user.username}.'
                    )},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(following=interest_user, user=request.user)
            serializer = SubscriptionsSerializer(
                interest_user,
                context={
                    'request': request
                },
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        subscribe = Follow.objects.filter(
            following=interest_user,
            user=request.user
        )
        if subscribe.exists():
            subscribe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': (
                    'Вы не были подписаны на пользователя '
                    + f'{interest_user.username}.'
            )},
            status=status.HTTP_400_BAD_REQUEST
        )
