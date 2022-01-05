from django.contrib import admin
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages
from .models import QuestionOption
from .models import Question
from .models import Voting
from census.models import Census

import datetime


from .filters import StartedFilter


def start(modeladmin, request, queryset):
    for v in queryset.all():
        v.create_pubkey()
        v.start_date = timezone.now()
        voter=request.user.id

        for u in User.objects.all():
            if(u.is_superuser):
                Census.objects.get_or_create(voter_id=u.id, voting_id=v.id)
        
        v.save()


def stop(ModelAdmin, request, queryset):
    for v in queryset.all():
        v.end_date = timezone.now()
        v.save()


def tally(ModelAdmin, request, queryset):
    
    for v in queryset.filter(end_date__lt=timezone.now()):
        token = request.session.get('auth-token', '')
        v.tally_votes(request.user,token)
        

 
    

class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption


class QuestionAdmin(admin.ModelAdmin):
    inlines = [QuestionOptionInline]
    actions = ['delete_selected']

    def delete_selected(self,request,obj):
        for o in obj.all():
            i=0
            votings = Voting.objects.all()
            for v in votings:
                if isinstance(v.start_date,datetime.datetime):
                    if v.question.filter(id = o.id):
                            i+=1
            if i==0:
                o.delete()
            else:
                messages.add_message(request, messages.ERROR, "This question cannot be deleted because it is part of a started voting")

class VotingAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')
    readonly_fields = ('start_date', 'end_date', 'pub_key',
                       'tally', 'postproc')
    date_hierarchy = 'start_date'
    list_filter = (StartedFilter,)
    search_fields = ('name', )

    actions = [ start, stop, tally ]


admin.site.register(Voting, VotingAdmin)
admin.site.register(Question, QuestionAdmin)
