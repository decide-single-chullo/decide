import json
from django.views.generic import TemplateView
from django.conf import settings
from django.http import Http404

from base import mods


# TODO: check permissions and census

def check_next_q(context, current_q_pos, questions_len, r):
    context['current_q_pos'] = current_q_pos
    if current_q_pos == questions_len-1:
        context['last_question']=True
    else:
        next_question_id = r[0]['question'][current_q_pos+1]['id']
        context['next_question_id'] = next_question_id
        context['last_question']=False

def question_pos_by_id(q_list, question_id):
    i=0
    for question in q_list:
        if int(question['id']) == question_id:
            break
        else:
            i+=1

    return i

class BoothView(TemplateView):
    template_name = 'booth/booth.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vid = kwargs.get('voting_id', 0)
        context['voting_id'] = vid
        question_id = kwargs.get('question_id', 0)
        context['question_id']= question_id

        try:
            r = mods.get('voting', params={'id': vid})

            # Casting numbers to string to manage in javascript with BigInt
            # and avoid problems with js and big number conversion
            for k, v in r[0]['pub_key'].items():
                r[0]['pub_key'][k] = str(v)
            
            questions_len = len(r[0]['question'])
            current_q_pos = question_pos_by_id(r[0]['question'], question_id)

            check_next_q(context, current_q_pos , questions_len , r)

            context['voting'] = json.dumps(r[0])
            context['question'] = json.dumps(r[0]['question'][current_q_pos])
        except:
            raise Http404('This voting does not exist')

        context['KEYBITS'] = settings.KEYBITS

        return context
