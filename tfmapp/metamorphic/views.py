from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.views.generic import CreateView, UpdateView, TemplateView, ListView, DeleteView
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import DBInstance, Query
from .forms import DBInstanceForm, QueryForm
from .utils import get_conn_data, parse_query, run_statement, compare_results
import psycopg2
import simplejson
# Create your views here.

connection_data = None

class AjaxableResponseMixin:
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    """
    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        else:
            return response

    def form_valid(self, form):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super().form_valid(form)
        if self.request.is_ajax():
            data = {
                'pk': self.object.pk,
            }
            return JsonResponse(data)
        else:
            return response


class DashboardHome(LoginRequiredMixin, TemplateView):
    template_name = 'metamorphic/index.html'

    def get_context_data(self):
        context = super(DashboardHome, self).get_context_data()
        logged_user = User.objects.get(username=self.request.user)
        context["logged_user"] = logged_user
        return context


class DBCreateView(LoginRequiredMixin, AjaxableResponseMixin, CreateView):
    model = DBInstance
    template_name = 'metamorphic/create_dbinstance.html'
    success_url = reverse_lazy('metamorphic:db_list')
    form_class = DBInstanceForm


    def form_valid(self, form):
        user = User.objects.get(pk=self.request.user.id)
        form.instance.user = user
        self.object = form.save()
        return super(DBCreateView, self).form_valid(form)


class DBUpdateView(LoginRequiredMixin, UpdateView):
    model = DBInstance
    form_class = DBInstanceForm
    pk_url_kwarg = 'instance_id'
    template_name = 'metamorphic/update_dbinstance.html'
    success_url = reverse_lazy('metamorphic:db_list')


class DBDeleteView(LoginRequiredMixin, AjaxableResponseMixin, DeleteView):
    model = DBInstance
    pk_url_kwarg = 'instance_id'
    success_url = reverse_lazy('metamorphic:db_list')


class DBListView(LoginRequiredMixin,ListView):
    template_name = 'metamorphic/dbinstance.html'
    #context_object_name = 'project_list'
    model = DBInstance

    def get_context_data(self):
        context = super(DBListView, self).get_context_data()
        logged_user = User.objects.get(username=self.request.user)
        #all_instances = DBInstance.objects.prefetch_related("user").filter(Q(user=logged_user)).distinct()
        all_instances = DBInstance.objects.all()
        context["all_db_instances"] = all_instances
        context["db_form"] = DBInstanceForm()
        return context


class QueryListView(LoginRequiredMixin,ListView):
    template_name = 'metamorphic/query.html'
    #context_object_name = 'project_list'
    model = Query

    def get_context_data(self):
        context = super(QueryListView, self).get_context_data()
        logged_user = User.objects.get(username=self.request.user)
        #all_queries = DBInstance.objects.prefetch_related("user").filter(Q(user=logged_user)).distinct()
        all_queries = Query.objects.all()
        context["all_queries"] = all_queries
        #context["db_form"] = DBInstanceForm()
        return context

class QueryCreateView(LoginRequiredMixin, AjaxableResponseMixin, CreateView):
    model = Query
    template_name = 'metamorphic/create_query.html'
    success_url = reverse_lazy('metamorphic:query_list')
    form_class = QueryForm

    def form_valid(self, form):
        user = User.objects.get(pk=self.request.user.id)
        form.instance.user = user
        self.object = form.save()
        return super(QueryCreateView, self).form_valid(form)


class QueryUpdateView(LoginRequiredMixin, UpdateView):
    model = Query
    form_class = QueryForm
    pk_url_kwarg = 'query_id'
    template_name = 'metamorphic/update_query.html'
    success_url = reverse_lazy('metamorphic:query_list')


class QueryDeleteView(LoginRequiredMixin, AjaxableResponseMixin, DeleteView):
    model = Query
    pk_url_kwarg = 'query_id'
    success_url = reverse_lazy('metamorphic:query_list')


class QueryTextView(LoginRequiredMixin, AjaxableResponseMixin, DetailView):
    model = Query
    template_name = 'metamorphic/show_query.html'
    pk_url_kwarg = 'query_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_query = Query.objects.get(pk=self.kwargs['query_id'])
        context['query'] = current_query
        return context


class RelationsView(LoginRequiredMixin, TemplateView):
    template_name = 'metamorphic/relations.html'

    def get_context_data(self):
        context = super(RelationsView, self).get_context_data()
        logged_user = User.objects.get(username=self.request.user)
        all_queries = Query.objects.all()
        context["logged_user"] = logged_user
        context["all_queries"] = all_queries
        return context


def get_query(request, **kwargs):
    if request.is_ajax():
        query = Query.objects.get(pk=kwargs['query_id'])
        # response = main(query.query_text)
        get_conn_data(query.instance)
        original_result = run_statement(query.query_text)
        data = parse_query(query)
        if data["changes"]:
            changes_result = run_statement(data["changes"][0]["transformacion"])
            are_equal = compare_results(original_result, changes_result)
            if data["nullable"] and not are_equal["status"]:
                response = {"text": "Applying transformations", "nullable": data["nullable"], "status": 200, "print": data["changes"], "data": original_result["rows"],
                            "columns": original_result["columns"]}
        else:
            response = {"text": "No changes to apply", "nullable": data["nullable"], "status": 200, "print": data["changes"], "data": original_result["rows"],
                        "columns": original_result["columns"]}
        return JsonResponse(response)
