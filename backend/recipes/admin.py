from django.contrib import admin

from recipes.models import (FavoriteRecipeUser, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCartUser, Tag, TagRecipe)


class TagRecipeInline(admin.TabularInline):
    model = TagRecipe


class IngredientRecipeInline(admin.TabularInline):
    model = IngredientRecipe


class RecipeAdmin(admin.ModelAdmin):
    readonly_fields = ('num_favorite_recipes',)
    list_display = ('name', 'author', 'num_favorite_recipes',)
    list_filter = ('author', 'name', 'tags',)
    search_fields = ('name__startswith',)
    inlines = [TagRecipeInline, IngredientRecipeInline, ]

    def num_favorite_recipes(self, obj):
        """Общее число добавлений конкретного рецепта в избранное."""
        return FavoriteRecipeUser.objects.filter(recipe=obj).count()

    class Meta:
        model = Recipe


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    list_filter = ('name',)


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'color', 'slug')
    list_filter = ('name',)


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(FavoriteRecipeUser)
admin.site.register(IngredientRecipe)
admin.site.register(TagRecipe)
admin.site.register(ShoppingCartUser)
admin.site.register(Tag, TagAdmin)
