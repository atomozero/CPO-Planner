# cpo_planner/projects/forms/subproject_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models.subproject import SubProject
from ..models.municipality import Municipality

class SubProjectForm(forms.ModelForm):
    class Meta:
        model = SubProject
        fields = [
            'name', 'municipality', 'description', 'start_date',
            'expected_completion_date', 'budget', 'expected_revenue',
            'roi', 'status'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        self.project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)
        
        # Opzionalmente, filtra i comuni disponibili
        # self.fields['municipality'].queryset = Municipality.objects.all().order_by('name')