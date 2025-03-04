# cpo_planner/projects/forms/project_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models.project import Project

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'description', 'region', 'start_date', 
            'expected_completion_date', 'total_budget', 
            'total_expected_revenue', 'status', 'photovoltaic_integration'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }