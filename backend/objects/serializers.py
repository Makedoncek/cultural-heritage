from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

        extra_kwargs = {
            'password': {
                'write_only': True,
                'required': True,
                'style': {'input_type': 'password'},
            },
            'email': {
                'required': True
            }
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Користувач з такою електронною поштою вже існує'
            )
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({
                'password2': 'Паролі не співпадають'
            })

        try:
            validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({
                'password': list(e.messages)
            })

        return data

    def create(self, validated_data):
        validated_data.pop('password2')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        return user