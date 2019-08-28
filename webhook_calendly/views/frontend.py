from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.db.models import Count, Prefetch, F, Subquery, OuterRef
from bookings.models import Booking
from ..models import ApprovalGroup, BookingCalendlyData
import re
from constance import config
from django.utils.html import strip_tags
from django.contrib.admin.views.decorators import staff_member_required
from django import forms


def generate_student_reports_list(event_type_id):
    '''
    Please be aware that the first group is the non-group
    '''
    BCD_obj = BookingCalendlyData.objects.filter(
            booking__event_type_id=event_type_id,
            booking__cancelled_at=None
        )

    groups_list = ApprovalGroup.objects.filter(
        approval_type=ApprovalGroup.APPROVAL_TYPE_FIRST_BOOKED
    ).prefetch_related(
        Prefetch('bookingcalendlydata_set',
            to_attr='current_bookings',
            queryset=BCD_obj.order_by('booking__booked_at')
        )
    ).prefetch_related('invitee_set')

    # Execute
    groups_list = list(groups_list)

    # Append non-group result
    non_group = ApprovalGroup(name='')
    non_group.current_bookings = list(
        BCD_obj.filter(approval_group=None).order_by('booking__booked_at')
    )
    non_group.approval_type = config.APPROVAL_NO_GROUP_ACTION
    non_group.is_non_group = True
    groups_list.append(non_group)

    bookings_list = []

    for g in groups_list:
        # find first approved spot
        # g.current_bookings is booked_at asc
        g.first_booking = None
        g.approval_statuses = {slug: [] for slug, name in Booking.APPROVAL_STATUS_CHOICES}
        for b in g.current_bookings:
            g.approval_statuses[b.booking.approval_status].append(b)
            if g.name and not g.first_booking and (b.booking.approval_status == Booking.APPROVAL_STATUS_APPROVED):
                g.first_booking = b

        if g.first_booking:
            # only first booking will be inserted to bookings_list
            bookings_list.append(g.first_booking)

        g.declined_bookings_count = len(g.approval_statuses[Booking.APPROVAL_STATUS_DECLINED])

    def natural_sort(l):
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key.name) ]
        l.sort(key = alphanum_key)

    natural_sort(groups_list)

    return groups_list, bookings_list


def get_default_event_type_id():
    event_type_id = None
    if config.DEFAULT_EVENT_TYPE_ID:
        event_type_id = config.DEFAULT_EVENT_TYPE_ID
    else:
        latest_spot_booking = Booking.objects.order_by('-spot_start').only('event_type_id').first()
        if latest_spot_booking:
            event_type_id = latest_spot_booking.event_type_id

    return event_type_id


def student_reports(request: HttpRequest):
    event_type_id = get_default_event_type_id()
    declined_bookings_count = 0
    groups_list = []
    bookings_list = []

    if event_type_id:
        groups_list, bookings_list = generate_student_reports_list(event_type_id)

        # This includes non-group number
        declined_bookings_count = sum(map(lambda g: g.declined_bookings_count, groups_list))

    context = {
        'announcement': config.ANNOUNCEMENT,
        'declined_bookings_count': declined_bookings_count,
        'groups_list': groups_list[1:], # except non-group
        'bookings_list': bookings_list,
    }

    if 'text/plain' in request.META.get('HTTP_ACCEPT') or request.GET.get('geek'):
        context['announcement'] = strip_tags(context['announcement'])
        return render(request, 'bookings/student_reports.txt', context, content_type="text/plain")
    else:
        return render(request, 'bookings/student_reports.html', context)


@staff_member_required
def admin_reports(request: HttpRequest):
    if 'event_type_id' in request.GET:
        event_type_id = request.GET['event_type_id']
    else:
        event_type_id = get_default_event_type_id()

    event_type_ids = Booking.objects.order_by().values('event_type_id').annotate(total=Count('id'))
    event_type_ids_choices = [
        (et['event_type_id'], "{} ({}{})".format(
            et['event_type_id'], et['total'], ', current' if et['event_type_id'] == event_type_id else ''
        ))
        for et in event_type_ids
    ]

    class EventTypeIdForm(forms.Form):
        event_type_id = forms.ChoiceField(label='Event Type', choices=event_type_ids_choices)

    form = EventTypeIdForm(request.GET if 'event_type_id' in request.GET else None)

    if event_type_id:
        groups_list, bookings_list = generate_student_reports_list(event_type_id)

        if groups_list[0].current_bookings:
            groups_list[0].name = 'Outliners'
        else:
            groups_list.pop(0)

    context = {
        'event_type_id': event_type_id,
        'event_type_ids': event_type_ids,
        'event_type_ids_form': form,
        'groups_list': groups_list,
        'bookings_list': bookings_list,
    }
    return render(request, 'bookings/admin_reports.html', context)