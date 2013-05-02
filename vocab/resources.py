from django.db.models import Q
from serrano.resources.datafield.values import DataFieldValues
from restlib2.http import codes

class ItemResource(DataFieldValues):
    def get(self, request, pk):
        item = self.get(request, pk=pk)

        if item is None:
            return codes.NOT_FOUND
        return item

class ItemResourceCollection(DataFieldValues):
    search_enabled = True
    max_results = 100
    order_by = None

    def get(self, request):
        queryset = self.queryset(request)

        order_by = self.order_by
        if not order_by:
            order_by = (queryset.model.description_field,)

        # search if enabled
        if self.search_enabled and request.GET.has_key('q'):
            kwargs = {}
            q = request.GET['q']
            query = Q()

            for field in getattr(self.model, 'search_fields', ()):
                query = query | Q(**{'%s__icontains' % field: q})

            queryset = queryset.order_by('-parent', *order_by)

            return queryset.filter(query)[:self.max_results]

        # get all root items by default
        return queryset.filter(parent=None).order_by(*order_by)

