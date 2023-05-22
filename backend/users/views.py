from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.pagination import CustomPagination
from api.serializers import (NewUserSerializer, SetPasswordSerializer,
                             SubscriptionsSerializer, UserSerializer)
from users.models import Follow, User


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
        if serializer.is_valid():
            if check_password(request.data['current_password'], user.password):
                new_password = make_password(request.data['new_password'])
                user.password = new_password
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {
                        'current_password':
                            'Введенный и текущий пароли не совпадают'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        serializer.is_valid()
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
        if subscribe:
            subscribe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': (
                    'Вы не были подписаны на пользователя '
                    + f'{interest_user.username}.'
            )},
            status=status.HTTP_400_BAD_REQUEST
        )
