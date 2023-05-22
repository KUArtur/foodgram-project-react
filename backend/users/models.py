from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER = 'user'
    ADMIN = 'admin'

    ROLES = [
        (USER, 'Пользователь'),
        (ADMIN, 'Администратор'),
    ]

    username = models.CharField(
        verbose_name='Логин',
        max_length=150,
        unique=True,
        blank=False,
        error_messages={
            'unique': ("Пользователь с таким логином уже существует"),
        },
    )
    first_name = models.CharField(verbose_name='Имя', max_length=150)
    last_name = models.CharField(verbose_name='Фамилия', max_length=150)
    email = models.EmailField(
        verbose_name='Почта',
        max_length=254,
        unique=True,
    )
    role = models.CharField(
        verbose_name='Роль пользователя',
        max_length=16,
        choices=ROLES,
        default=USER,
        blank=True
    )
    password = models.CharField(verbose_name='Пароль', max_length=150)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [
        'username',
        'first_name',
        'last_name',
        'password',
    ]
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-id']

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == self.ADMIN


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower",
        verbose_name="Подписавшийся",
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name="Автор",
    )

    class Meta:
        verbose_name = 'Мои подписки'
        verbose_name_plural = 'Мои подписки'
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "following_id"], name="unique_follow"
            )
        ]

    def __str__(self):
        return (
            f"{self.user.username} подписался на автора"
            f" {self.following.username}"
        )