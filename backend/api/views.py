from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.response import Response

from recipes.models import (
    Follow, Recipe, Ingredient, Tag, 
    RecipeIngredient, Favorite, ShoppingCart)
from .serializers import (
    RecipeSerializer, IngredientSerializer,
    TagSerializer, MinRecipeSerializer)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.add_obj(Favorite, request.user, pk)
        elif request.method == 'DELETE':
            return self.delete_obj(Favorite, request.user, pk)
        return None

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self.add_obj(ShoppingCart, request.user, pk)
        elif request.method == 'DELETE':
            return self.delete_obj(ShoppingCart, request.user, pk)
        return None

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        purchases = user.shopping_cart.all()
        shopping_cart = {}
        for purchase in purchases:
            ingredients = RecipeIngredient.objects.filter(
                recipe=purchase.recipe
            ).all()
            for ingredient in ingredients:
                name = ingredient.ingredient.name
                amount = ingredient.amount
                if name not in shopping_cart.keys():
                    shopping_cart[name] = amount
                else:
                    shopping_cart[name] += amount
        final_list={}
        for ingredient, amount in shopping_cart.items():
            measurement_unit = get_object_or_404(
                Ingredient, name=ingredient
            ).measurement_unit
            final_list[ingredient] = {
                'amount': amount,
                'measurement_unit': measurement_unit
                    
            }
        pdfmetrics.registerFont(
            TTFont('DejaVuSans','DejaVuSans.ttf', 'UTF-8'))
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping_list.pdf"')
        page = canvas.Canvas(response)
        page.setFont('DejaVuSans', size=24)
        page.drawString(200, 800, 'Список ингредиентов')
        page.setFont('DejaVuSans', size=16)
        height = 750
        for i, (name, data) in enumerate(final_list.items(), 1):
            page.drawString(75, height, (f'<{i}> {name} - {data["amount"]}, '
                                         f'{data["measurement_unit"]}'))
            height -= 25
        page.showPage()
        page.save()
        return response

    def add_obj(self, model, user, pk):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            return Response({
                'message': 'Recipe is already in a list'
            }, status=status.HTTP_400_BAD_REQUEST)
        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = MinRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_obj(self, model, user, pk):
        obj = model.objects.filter(user=user, recipe__id=pk)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({
            'message': 'Recipe has already been deleted'
        }, status=status.HTTP_400_BAD_REQUEST)
