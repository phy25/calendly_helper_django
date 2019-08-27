from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.db.models import Count, Prefetch, F, Subquery, OuterRef
from bookings.models import Booking
from ..models import ApprovalGroup, BookingCalendlyData
import re
from constance import config
from django.utils.html import strip_tags

def generate_student_reports_list(event_type_id):
    groups_list = ApprovalGroup.objects.filter(
        #approval_type=ApprovalGroup.APPROVAL_TYPE_ONE_SPOT
    ).prefetch_related(
        Prefetch('bookingcalendlydata_set',
            to_attr='current_bookings',
            queryset=BookingCalendlyData.objects.filter(
                booking__event_type_id=event_type_id
            ).order_by('booking__booked_at')
        )
    )

    # Execute
    groups_list = list(groups_list)

    bookings_list = []

    for g in groups_list:
        # find first approved spot
        # g.current_bookings is booked_at asc
        g.first_booking = None
        for b in g.current_bookings:
            if b.booking.approval_status == Booking.APPROVAL_STATUS_APPROVED:
                g.first_booking = b
                break

        if not g.first_booking:
            g.row_class = 'table-warning'
        else:
            # only first booking will be inserted to bookings_list
            bookings_list.append(g.first_booking)

        g.declined_bookings_count = len(list(filter(
            lambda b: b.booking.approval_status == Booking.APPROVAL_STATUS_DECLINED
        , g.current_bookings)))

        #if g.declined_bookings_count:
        #    g.row_class = 'table-warning'

    def natural_sort(l):
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key.name) ]
        l.sort(key = alphanum_key)

    natural_sort(groups_list)
    return groups_list, bookings_list


def student_reports(request: HttpRequest):
    if config.DEFAULT_EVENT_TYPE_ID:
        event_type_id = config.DEFAULT_EVENT_TYPE_ID
    else:
        latest_spot_booking = Booking.objects.order_by('-spot_start').only('event_type_id').first()

        if latest_spot_booking:
            event_type_id = latest_spot_booking.event_type_id

    if event_type_id:
        declined_bookings_count = Booking.objects.filter(
            approval_status=Booking.APPROVAL_STATUS_DECLINED,
            event_type_id=event_type_id
        ).aggregate(Count('id'))['id__count']

        groups_list, bookings_list = generate_student_reports_list(event_type_id)

    context = {
        'announcement': config.ANNOUNCEMENT,
        'declined_bookings_count': declined_bookings_count,
        'groups_list': groups_list,
        'bookings_list': bookings_list,
    }

    if 'text/plain' in request.META.get('HTTP_ACCEPT') or request.GET.get('geek'):
        context['announcement'] = strip_tags(context['announcement'])
        return render(request, 'bookings/student_reports.txt', context, content_type="text/plain")
    else:
        return render(request, 'bookings/student_reports.html', context)
