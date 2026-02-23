from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Tag, CulturalObject


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


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'icon']
        read_only_fields = ['id', 'name', 'slug', 'icon']


class ObjectListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source='author.username',
        read_only=True
    )

    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = CulturalObject
        fields = [
            'id',
            'title',
            'latitude',
            'longitude',
            'status',
            'author_name',
            'tags'
        ]
        read_only_fields = fields


class ObjectDetailSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = CulturalObject
        fields = '__all__'

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class ObjectWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        help_text="Список ID тегів (1-5 тегів обов'язково)"
    )

    class Meta:
        model = CulturalObject
        fields = [
            'title',
            'description',
            'latitude',
            'longitude',
            'tags',
            'wikipedia_url',
            'official_website',
            'google_maps_url'
        ]

    def validate_tags(self, value):
        if len(value) < 1:
            raise serializers.ValidationError(
                "Культурний об'єкт повинен мати мінімум 1 тег"
            )

        if len(value) > 5:
            raise serializers.ValidationError(
                "Культурний об'єкт повинен мати не більше 5 тегів"
            )

        return value

    def validate(self, data):
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude is not None:
            if latitude < 44.0 or latitude > 52.5:
                raise serializers.ValidationError({
                    'latitude': 'Координати поза межами України (допустимі значення широти: 44.0 - 52.5)'
                })

        if longitude is not None:
            if longitude < 22.0 or longitude > 40.5:
                raise serializers.ValidationError({
                    'longitude': 'Координати поза межами України (допустимі значення довготи: 22.0 - 40.5)'
                })
        return data
