from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from sorting_bootstrap.util import label_for_field

register = template.Library()


def result_headers(context, cl): 
    """
    Generates the list column headers.
    """
    for i, field_name in enumerate(cl.list_display):
        text, attr = label_for_field(field_name, cl.model, return_attr=True)
        if attr:
            # Potentially not sortable

            # if the field is the action checkbox: no sorting and special class
            if field_name == 'action_checkbox':
                yield {
                    "text": text,
                    "class_attrib": mark_safe(' class="action-checkbox-column"'),
                    "sortable": False,
                }
                continue

#            if other_fields like Edit, Visualize, etc:
                # Not sortable
#                yield {
#                    "text": text,
#                    "class_attrib": format_html(' class="column-{0}"', field_name),
#                    "sortable": False,
#                }
#                continue

        # OK, it is sortable if we got this far
        th_classes = ['sortable', 'column-{0}'.format(field_name)]
        ascending = None
        sorted = False
        # Is it currently being sorted on?
        if context.get('current_sort_field') == field_name:
            sorted = True
            ascending = False
            th_classes.append('sorted descending')
        elif context.get('current_sort_field') == '-'+field_name:
            sorted = True
            ascending = True
            th_classes.append('sorted ascending')

### TO-DO: when start using action_checkbox use i instead of i + 1. This +1 is to correct enumerate index
        # builds url
        url = "./?sort_by="
        if ascending is False:
            url += "-"
        url += str(i + 1)

        if 'getsortvars' in context:
            extra_vars = context['getsortvars']
        else:
            if 'request' in context:
                request = context['request']
                getvars = request.GET.copy()
                if 'sort_by' in getvars:
                    del getvars['sort_by']
                if len(getvars.keys()) > 0:
                    context['getsortvars'] = "&%s" % getvars.urlencode()
                else:
                    context['getsortvars'] = ''
                extra_vars = context['getsortvars']

        # append other vars to url
        url += extra_vars

        yield {
            "text": text,
            "url": url,
            "sortable": True,
            "sorted": sorted,
            "ascending": ascending,
            "class_attrib": format_html(' class="{0}"', ' '.join(th_classes)) if th_classes else '',
        }


@register.inclusion_tag('sorting_bootstrap/sort_headers_frag.html', takes_context=True)
def sort_headers(context, cl):
    """
    Displays the headers and data list together
    """
    headers = list(result_headers(context, cl))
    sorted_fields = False
    for h in headers:
        if h['sortable'] and h['sorted']:
            sorted_fields = True
    return {'cl': cl,
            'result_headers': headers,
            'sorted_fields': sorted_fields}


def sort_link(context, text, sort_field, visible_name=None):
    """Usage: {% sort_link "text" "field_name" %}
    Usage: {% sort_link "text" "field_name" "Visible name" %}
    """
    sorted_fields = False
    ascending = None
    class_attrib = 'sortable'
    orig_sort_field = sort_field
    if context.get('current_sort_field') == sort_field:
        sort_field = '-%s' % sort_field
        visible_name = '-%s' % (visible_name or orig_sort_field)
        sorted_fields = True
        ascending = False
        class_attrib += ' sorted descending'
    elif context.get('current_sort_field') == '-'+sort_field:
        visible_name = '%s' % (visible_name or orig_sort_field)
        sorted_fields = True
        ascending = True
        class_attrib += ' sorted ascending'

    if visible_name:
        if 'request' in context:
            request = context['request']
            request.session[visible_name] = sort_field

    # builds url
    url = "./?sort_by="
    if visible_name is None:
        url += sort_field
    else:
        url += visible_name

    if 'getsortvars' in context:
        extra_vars = context['getsortvars']
    else:
        if 'request' in context:
            request = context['request']
            getvars = request.GET.copy()
            if 'sort_by' in getvars:
                del getvars['sort_by']
            if len(getvars.keys()) > 0:
                context['getsortvars'] = "&%s" % getvars.urlencode()
            else:
                context['getsortvars'] = ''
            extra_vars = context['getsortvars']

    # append other vars to url
    url += extra_vars

    return {
        'text': text, 'url': url, 'ascending': ascending, 'sorted_fields': sorted_fields, 'class_attrib': class_attrib
    }

# registers the tags sort_link and sort_th with the same function sort_link
register.inclusion_tag('sorting_bootstrap/sort_link_frag.html', takes_context=True, name='sort_link')(sort_link)
register.inclusion_tag('sorting_bootstrap/sort_th_frag.html', takes_context=True, name='sort_th')(sort_link)

@register.tag
def auto_sort(parser, token):
    "usage: {% auto_sort queryset %}"
    try:
        tag_name, queryset = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires a single argument" % token.contents.split()[0]
    return SortedQuerysetNode(queryset)


class SortedQuerysetNode(template.Node):
    def __init__(self, queryset):
        self.queryset_var = queryset
        self.queryset = template.Variable(queryset)

    def render(self, context):
        queryset = self.queryset.resolve(context)
        if 'request' in context:
            request = context['request']
            sort_by = request.GET.get('sort_by')
            has_visible_name = False
            if sort_by:
                if sort_by in [el.name for el in queryset.model._meta.fields]:
                    queryset = queryset.order_by(sort_by)
                else:
                    has_visible_name = True
                    if sort_by in request.session:
                        sort_by = request.session[sort_by]
                        try:
                            queryset = queryset.order_by(sort_by)
                        except:
                            raise
        context[self.queryset_var] = queryset
        if 'request' in context:
            getvars = request.GET.copy()
        else:
            getvars = {}
        if 'sort_by' in getvars:
            if has_visible_name:
                context['current_sort_field'] = request.session.get(getvars['sort_by']) or getvars['sort_by']
            else:
                context['current_sort_field'] = getvars['sort_by']
            del getvars['sort_by']
        if len(getvars.keys()) > 0:
            context['getsortvars'] = "&%s" % getvars.urlencode()
        else:
            context['getsortvars'] = ''
        return ''