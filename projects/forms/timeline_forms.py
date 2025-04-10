# cpo_planner/projects/forms/timeline_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models.timeline import ProjectTimeline, StationTimeline

class ProjectTimelineForm(forms.ModelForm):
    """Form per il cronoprogramma del progetto"""
    
    class Meta:
        model = ProjectTimeline
        fields = [
            'planning_start', 'planning_end',
            'permitting_start', 'permitting_end',
            'procurement_start', 'procurement_end',
            'installation_start', 'installation_end',
            'testing_start', 'testing_end',
            'operation_start', 'timeline_notes',
            'critical_milestones'
        ]
        
        widgets = {
            'planning_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'planning_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'permitting_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'permitting_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'procurement_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'procurement_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'installation_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'installation_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'testing_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'testing_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'operation_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'timeline_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'critical_milestones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Raggruppa i campi in fasi
        self.planning_fields = ['planning_start', 'planning_end']
        self.permitting_fields = ['permitting_start', 'permitting_end']
        self.procurement_fields = ['procurement_start', 'procurement_end']
        self.installation_fields = ['installation_start', 'installation_end']
        self.testing_fields = ['testing_start', 'testing_end']
        self.operation_fields = ['operation_start']
        self.notes_fields = ['timeline_notes', 'critical_milestones']

class StationTimelineForm(forms.ModelForm):
    """Form per il cronoprogramma della stazione"""
    
    class Meta:
        model = StationTimeline
        fields = [
            'design_start', 'design_end',
            'permit_application_date', 'permit_approval_date',
            'equipment_order_date', 'equipment_delivery_date',
            'site_preparation_start', 'site_preparation_end',
            'installation_start', 'installation_end',
            'grid_connection_date', 'testing_date',
            'commissioning_date', 'status_notes'
        ]
        
        widgets = {
            'design_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'design_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'permit_application_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'permit_approval_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'equipment_order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'equipment_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'site_preparation_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'site_preparation_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'installation_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'installation_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'grid_connection_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'testing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'commissioning_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Raggruppa i campi in fasi
        self.design_fields = ['design_start', 'design_end']
        self.permit_fields = ['permit_application_date', 'permit_approval_date']
        self.equipment_fields = ['equipment_order_date', 'equipment_delivery_date']
        self.preparation_fields = ['site_preparation_start', 'site_preparation_end']
        self.installation_fields = ['installation_start', 'installation_end']
        self.final_fields = ['grid_connection_date', 'testing_date', 'commissioning_date']
        self.notes_fields = ['status_notes']