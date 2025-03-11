from django.core.management.base import BaseCommand
from infrastructure.models import ChargingStationTemplate

class Command(BaseCommand):
    help = 'Updates charging station templates to have ground_area values'

    def handle(self, *args, **options):
        templates = ChargingStationTemplate.objects.all()
        if not templates.exists():
            self.stdout.write(self.style.WARNING('No templates found'))
            return
            
        count = 0
        for template in templates:
            if template.ground_area is None:
                # Set a default ground area based on power
                if template.power_kw <= 22:
                    template.ground_area = 2.0
                elif template.power_kw <= 50:
                    template.ground_area = 3.0
                else:
                    template.ground_area = 4.0
                    
                template.save()
                count += 1
                self.stdout.write(f'Updated template {template.id}: {template.brand} {template.model}, power={template.power_kw}, ground_area={template.ground_area}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} templates'))