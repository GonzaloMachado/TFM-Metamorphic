from django.shortcuts import render
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.views import generic
from .forms import UserCreateForm

# Create your views here.

class SignUp(generic.CreateView):
	model = User
	template_name = 'accounts/sign_up.html'
	form_class = UserCreateForm
	success_url = '/account/login'

	# def get_success_url(self, **kwargs):
	# 	return reverse('experiments:all-customers', kwargs={'project_id': self.object.id })

	# def form_valid(self, form):
	# 	user = User.objects.get(pk=self.request.user.id)
	# 	random_number = str(random.random()).encode('utf-8')
	# 	#We generate a random activation key
	# 	salt = hashlib.sha1(random_number).hexdigest()[:16]
	# 	usernamesalt = user.username
	# 	if isinstance(usernamesalt, bytes):
	# 		usernamesalt = usernamesalt.encode('utf-8')
	# 	invitation_key= hashlib.sha1(salt.encode()+usernamesalt.encode()).hexdigest()[:16]
	# 	form.instance.author_user = user
	# 	form.instance.invitation_key = invitation_key
	# 	self.object = form.save()
	# 	return super(NewProject, self).form_valid(form)