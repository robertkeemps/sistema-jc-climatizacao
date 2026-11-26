from django import forms
from .models import Os, Cliente

class OsForm(forms.ModelForm):
    dt_abertura_os = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    dt_visita = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    hr_visita = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}))
    dt_fim_os = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))

    class Meta:
        model = Os
        fields = [
            'id_cliente', 'dt_abertura_os', 'dt_visita', 'hr_visita',
            'status', 'dt_fim_os', 'vlr_total', 'pago', 'descricao', 'id_forma_pagto'
        ]
        widgets = {
            'id_cliente': forms.Select(attrs={'class': 'form-control'}),
            'id_forma_pagto': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'pago': forms.Select(attrs={'class': 'form-control'}),
            'vlr_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }