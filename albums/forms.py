from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.utils.html import strip_tags
from django.core.validators import RegexValidator

User = get_user_model() #Автоматически берёт юзера из settings.py из глобал переменной AUTH_USER_MODEL

class CustomUserCreationForm(UserCreationForm): 
    email = forms.EmailField(required=True, max_length=66,
                             widget=forms.EmailInput(attrs={'class': 'input-register form-control', 'placeholder': 'Введите свою почту'}))
    first_name = forms.CharField(required=True, max_length=25,
                         widget=forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Введите своё имя'}))
    last_name = forms.CharField(required=True, max_length=25,
                         widget=forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Введите свою фамилию'}))
    username = forms.CharField(required=True, max_length=25,
                         widget=forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Введите ваш никнейм'}))
    password1 = forms.CharField(required=True, max_length=25,
                         widget=forms.PasswordInput(attrs={'class': 'input-register form-control', 'placeholder': 'Введите ваш пароль'}))
    password2 = forms.CharField(required=True, max_length=25,
                         widget=forms.PasswordInput(attrs={'class': 'input-register form-control', 'placeholder': 'Подтвердите ваш пароль'}))
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2', 'username')

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        username = cleaned_data.get('username')
        
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Почта занята!')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username занят!')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user
    
class CustomUserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Email или Username',
        widget=forms.TextInput(attrs={'autofocus': True, 'class': 'input-register form-control', 'placeholder': 'Введите почту или ник'})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'autofocus': True, 'class': 'input-register form-control', 'placeholder': 'Ваш Пароль'})
    )
    
    def clean(self):
        cd = self.cleaned_data
        username = cd.get('username')
        password = cd.get('password')

        if username and password:
            user = authenticate(self.request, username=username, password=password)
            if not user:
                try:
                    user_obj = User.objects.get(username=username)
                    user = authenticate(self.request, username=user_obj.email, password=password)
                except User.DoesNotExist:
                    user = None
            if user is None:
                raise forms.ValidationError('Неверный логин или пароль!')
            elif not user.is_active:
                raise forms.ValidationError('Your account is inactive!')
            self.user_cache = user
            
        return cd
    
class CustomUserUpdateForm(forms.ModelForm):
    username = forms.CharField(
        required=True,
        max_length=25,
        widget=forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Ваш никнейм'})
    )
    first_name = forms.CharField(
        required=True,
        max_length=25,
        widget=forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Ваше имя'})
    )
    last_name = forms.CharField(
        required=True,
        max_length=25,
        widget=forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Ваша фамилия'})
    )
    email = forms.EmailField(
        required=True,
        max_length=66,
        widget=forms.EmailInput(attrs={'class': 'input-register form-control', 'placeholder': 'Ваша почта'})
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username')
        widgets = {
            'email' : forms.EmailInput(attrs={'class': 'input-register form-control', 'placeholder': 'Ваша почта'}),
            'first_name' : forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Ваше имя'}),
            'last_name' : forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Ваша фамилия'}),
            'username' : forms.TextInput(attrs={'class': 'input-register form-control', 'placeholder': 'Ваш никнейм'})
        }


    def clean(self):
        cd = super().clean()
        email = cd.get('email')
        username = cd.get('username')
        
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Эта почта уже используется!')
        
        if username and User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Этот никнейм уже используется!')
        
        return cd
