from django.utils import timezone

def update_production_order_status(production_order):
    """
    Automatically update the status of a production order 
    if the last scheduled operation is finished.
    """
    last_schedule = (
        production_order.machinescheduling_set
        .order_by('-seq')
        .first()
    )
    if last_schedule and timezone.now() > last_schedule.scheduled_end:
        # ✅ Set order_status to id=3 (assuming that's the right StatusAction)
        production_order.order_status_id = 3  
        production_order.save(update_fields=['order_status'])