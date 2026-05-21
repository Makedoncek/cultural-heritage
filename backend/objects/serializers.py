from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Tag, CulturalObject, Favorite, FavoriteAuthor, ObjectPhoto, ObjectAudio, InaccuracyReport, Visit, PlannedVisit
from .validators import validate_coordinates_within_ukraine


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['is_staff'] = user.is_staff
        return token

    def validate(self, attrs):
        # Дозволяємо логін як по username, так і по email.
        login = attrs.get(self.username_field, '')
        if '@' in login:
            try:
                user = User.objects.get(email__iexact=login)
                attrs[self.username_field] = user.username
            except User.DoesNotExist:
                pass  # fallthrough — super().validate видасть помилку про невірні дані
        return super().validate(attrs)


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
            password=validated_data['password'],
            is_active=False,
        )

        return user


class TagSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'icon', 'tag_type']
        read_only_fields = ['id', 'name', 'slug', 'icon', 'tag_type']

    def get_name(self, obj):
        """Return English name when the request locale is English; otherwise fall back to `name`."""
        from django.utils.translation import get_language
        if get_language() == 'en' and getattr(obj, 'name_en', ''):
            return obj.name_en
        return obj.name


class FavoriteMixin(serializers.Serializer):
    is_favorited = serializers.SerializerMethodField()
    favorites_count = serializers.IntegerField(read_only=True, default=0)

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if hasattr(obj, '_is_favorited'):
                return obj._is_favorited
            return Favorite.objects.filter(user=request.user, cultural_object=obj).exists()
        return False


class ObjectListSerializer(FavoriteMixin, serializers.ModelSerializer):
    author_name = serializers.CharField(
        source='author.username',
        read_only=True
    )

    tags = TagSerializer(many=True, read_only=True)
    cover_url = serializers.CharField(read_only=True, allow_null=True)
    is_visited = serializers.SerializerMethodField()

    class Meta:
        model = CulturalObject
        fields = [
            'id',
            'title',
            'latitude',
            'longitude',
            'status',
            'object_type',
            'event_start_date',
            'event_end_date',
            'author_name',
            'tags',
            'created_at',
            'is_favorited',
            'favorites_count',
            'cover_url',
            'is_visited',
        ]
        read_only_fields = fields

    def get_is_visited(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if hasattr(obj, '_is_visited'):
            return obj._is_visited
        return Visit.objects.filter(user=request.user, cultural_object=obj).exists()


class ObjectDetailSerializer(FavoriteMixin, serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    photos = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()
    cover_url = serializers.CharField(read_only=True, allow_null=True)
    is_visited = serializers.SerializerMethodField()
    is_planned = serializers.SerializerMethodField()
    visits_count = serializers.SerializerMethodField()

    class Meta:
        model = CulturalObject
        fields = [
            'id', 'title', 'description',
            'latitude', 'longitude',
            'author', 'tags',
            'status', 'object_type',
            'event_start_date', 'event_end_date',
            'wikipedia_url', 'official_website', 'google_maps_url',
            'created_at', 'updated_at', 'archived_at',
            'is_favorited', 'favorites_count',
            'photos', 'photo_count', 'cover_url',
            'is_visited', 'is_planned', 'visits_count',
        ]

    def get_is_visited(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Visit.objects.filter(user=request.user, cultural_object=obj).exists()

    def get_is_planned(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return PlannedVisit.objects.filter(user=request.user, cultural_object=obj).exists()

    def get_visits_count(self, obj):
        return Visit.objects.filter(cultural_object=obj).count()

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_photos(self, obj):
        request = self.context.get('request')
        qs = obj.photos.all()
        if request and request.user.is_authenticated:
            if not request.user.is_staff:
                qs = qs.filter(Q(status='approved') | Q(uploaded_by=request.user))
        else:
            qs = qs.filter(status='approved')
        return ObjectPhotoSerializer(qs, many=True, context=self.context).data

    def get_photo_count(self, obj):
        return obj.photos.filter(status='approved').count()


class ObjectWithMyPhotosSerializer(ObjectListSerializer):
    """Об'єкт + масив фото, які завантажив поточний користувач (для /with-my-photos/)."""
    my_photos = serializers.SerializerMethodField()

    class Meta(ObjectListSerializer.Meta):
        fields = list(ObjectListSerializer.Meta.fields) + ['my_photos']
        read_only_fields = fields

    def get_my_photos(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        # prefetch_related у view ставить кеш на `photos`, тож фільтр у Python — без зайвого SQL
        photos = [p for p in obj.photos.all() if p.uploaded_by_id == request.user.id]
        photos.sort(key=lambda p: p.created_at, reverse=True)
        return ObjectPhotoSerializer(photos, many=True, context=self.context).data


class UserProfileSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    approved_objects_count = serializers.IntegerField(read_only=True, default=0)
    total_favorites_received = serializers.IntegerField(read_only=True, default=0)
    followers_count = serializers.IntegerField(read_only=True, default=0)
    is_followed = serializers.BooleanField(read_only=True, default=False)
    email = serializers.SerializerMethodField()

    def get_email(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.pk == obj.pk:
            return obj.email
        return None


class ObjectWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        help_text="Список ID тегів (1-5 тегів обов'язково)"
    )

    class Meta:
        model = CulturalObject
        fields = [
            'id',
            'title',
            'description',
            'latitude',
            'longitude',
            'tags',
            'object_type',
            'event_start_date',
            'event_end_date',
            'wikipedia_url',
            'official_website',
            'google_maps_url',
            'status',
        ]
        read_only_fields = ['id', 'status']

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

        if self.instance:
            if latitude is None:
                latitude = self.instance.latitude
            if longitude is None:
                longitude = self.instance.longitude

        if latitude is not None and longitude is not None:
            try:
                validate_coordinates_within_ukraine(latitude, longitude)
            except DjangoValidationError as e:
                raise serializers.ValidationError({
                    'coordinates': e.message
                })

        object_type = data.get('object_type', getattr(self.instance, 'object_type', 'permanent'))
        if object_type == CulturalObject.ObjectType.EVENT:
            start = data.get('event_start_date')
            end = data.get('event_end_date')
            if not start or not end:
                raise serializers.ValidationError({
                    'event_start_date': 'Для подій потрібно вказати дату початку та завершення.'
                })
            if end < start:
                raise serializers.ValidationError({
                    'event_end_date': 'Дата завершення не може бути раніше дати початку.'
                })
            if not self.instance and end < timezone.now():
                raise serializers.ValidationError({
                    'event_end_date': 'Подія вже завершилась.'
                })
        else:
            data['event_start_date'] = None
            data['event_end_date'] = None

        return data


class UploadedByNestedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class ObjectPhotoSerializer(serializers.ModelSerializer):
    uploaded_by = UploadedByNestedSerializer(read_only=True)

    class Meta:
        model = ObjectPhoto
        fields = [
            'id',
            'cultural_object',
            'uploaded_by',
            'image_url',
            'thumbnail_url',
            'caption',
            'status',
            'order',
            'is_author_photo',
            'created_at',
        ]
        read_only_fields = [
            'id', 'cultural_object', 'uploaded_by', 'image_url',
            'thumbnail_url', 'status', 'order', 'is_author_photo', 'created_at',
        ]


class ObjectAudioSerializer(serializers.ModelSerializer):
    uploaded_by = UploadedByNestedSerializer(read_only=True)
    language_label = serializers.CharField(source='get_language_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ObjectAudio
        fields = [
            'id', 'cultural_object', 'uploaded_by',
            'cloudinary_url', 'duration_seconds',
            'language', 'language_label',
            'title', 'narrator_name',
            'status', 'status_label', 'moderation_note',
            'plays_count', 'created_at',
        ]
        read_only_fields = [
            'id', 'cultural_object', 'uploaded_by',
            'cloudinary_url', 'duration_seconds',
            'language_label', 'status', 'status_label',
            'moderation_note', 'plays_count', 'created_at',
        ]


class AudioUploadSerializer(serializers.Serializer):
    """Validates multipart upload of an audio narrative."""
    audio = serializers.FileField()
    language = serializers.ChoiceField(choices=ObjectAudio.Language.choices)
    title = serializers.CharField(max_length=150)
    narrator_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    copyright_confirmed = serializers.BooleanField()

    ALLOWED_MIMES = (
        'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/webm',
        'audio/ogg', 'audio/wav', 'audio/x-m4a', 'audio/x-wav',
    )
    MAX_SIZE_BYTES = 10 * 1024 * 1024

    def validate_audio(self, value):
        if value.size > self.MAX_SIZE_BYTES:
            raise serializers.ValidationError('Файл більший за 10 МБ')
        if value.content_type and value.content_type not in self.ALLOWED_MIMES:
            raise serializers.ValidationError(f'Непідтримуваний формат: {value.content_type}')
        return value

    def validate_copyright_confirmed(self, value):
        if not value:
            raise serializers.ValidationError(
                'Потрібно підтвердити авторство або право на публікацію'
            )
        return value


class InaccuracyReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    object_title = serializers.CharField(source='cultural_object.title', read_only=True)
    object_id = serializers.IntegerField(source='cultural_object.id', read_only=True)
    reason_label = serializers.CharField(source='get_reason_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = InaccuracyReport
        fields = [
            'id', 'object_id', 'object_title',
            'reporter_username', 'reason_type', 'reason_label',
            'note', 'status', 'status_label', 'admin_response',
            'created_at', 'resolved_at',
        ]
        read_only_fields = [
            'id', 'reporter_username', 'object_id', 'object_title',
            'reason_label', 'status', 'status_label', 'admin_response',
            'created_at', 'resolved_at',
        ]


def _object_cover_thumb(cultural_object) -> str | None:
    photo = cultural_object.photos.filter(status='approved').order_by(
        '-is_author_photo', 'order', 'created_at'
    ).first()
    return photo.thumbnail_url if photo else None


def _object_tag_payload(cultural_object) -> list[dict]:
    return [
        {'id': t.id, 'name': t.name, 'slug': t.slug, 'icon': t.icon, 'tag_type': t.tag_type}
        for t in cultural_object.tags.all()
    ]


class VisitSerializer(serializers.ModelSerializer):
    object_id = serializers.IntegerField(source='cultural_object_id', read_only=True)
    object_title = serializers.SerializerMethodField()
    object_cover_url = serializers.SerializerMethodField()
    object_tags = serializers.SerializerMethodField()

    class Meta:
        model = Visit
        fields = [
            'id', 'object_id', 'object_title', 'object_cover_url', 'object_tags',
            'visited_at', 'impression', 'is_public',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'object_id', 'object_title', 'object_cover_url', 'object_tags',
                            'created_at', 'updated_at']

    def get_object_title(self, obj):
        return obj.cultural_object.title

    def get_object_cover_url(self, obj):
        return _object_cover_thumb(obj.cultural_object)

    def get_object_tags(self, obj):
        return _object_tag_payload(obj.cultural_object)


class PlannedVisitSerializer(serializers.ModelSerializer):
    object_id = serializers.IntegerField(source='cultural_object_id', read_only=True)
    object_title = serializers.SerializerMethodField()
    object_cover_url = serializers.SerializerMethodField()
    object_tags = serializers.SerializerMethodField()

    class Meta:
        model = PlannedVisit
        fields = [
            'id', 'object_id', 'object_title', 'object_cover_url', 'object_tags',
            'planned_date', 'note', 'created_at',
        ]
        read_only_fields = ['id', 'object_id', 'object_title', 'object_cover_url', 'object_tags', 'created_at']

    def get_object_title(self, obj):
        return obj.cultural_object.title

    def get_object_cover_url(self, obj):
        return _object_cover_thumb(obj.cultural_object)

    def get_object_tags(self, obj):
        return _object_tag_payload(obj.cultural_object)


# --- Routes ---

class RouteStopSerializer(serializers.ModelSerializer):
    object_id = serializers.IntegerField(source='cultural_object_id', read_only=True)
    object_title = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    object_status = serializers.SerializerMethodField()
    object_cover_url = serializers.SerializerMethodField()
    is_unavailable = serializers.BooleanField(read_only=True)
    is_visited = serializers.SerializerMethodField()

    class Meta:
        from .models import RouteStop
        model = RouteStop
        fields = [
            'id', 'order', 'object_id', 'object_title',
            'latitude', 'longitude', 'object_status', 'object_cover_url',
            'note', 'is_unavailable', 'is_visited',
        ]
        read_only_fields = ['id', 'object_id', 'object_title', 'latitude', 'longitude',
                            'object_status', 'object_cover_url', 'is_unavailable', 'is_visited']

    def get_object_title(self, obj):
        return obj.cultural_object.title

    def get_latitude(self, obj):
        return str(obj.cultural_object.latitude)

    def get_longitude(self, obj):
        return str(obj.cultural_object.longitude)

    def get_object_status(self, obj):
        return obj.cultural_object.status

    def get_object_cover_url(self, obj):
        return _object_cover_thumb(obj.cultural_object)

    def get_is_visited(self, obj):
        # `visited_object_ids` injected by RouteViewSet.retrieve via context — avoids N+1.
        visited_ids = self.context.get('visited_object_ids')
        if visited_ids is None:
            return False
        return obj.cultural_object_id in visited_ids


class RouteListSerializer(serializers.ModelSerializer):
    from .models import Route
    author_name = serializers.CharField(source='author.username', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    stops_count = serializers.SerializerMethodField()

    class Meta:
        from .models import Route
        model = Route
        fields = [
            'id', 'title', 'description',
            'status', 'visibility', 'is_featured',
            'cover_photo', 'estimated_duration_minutes',
            'author_name', 'tags', 'stops_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_stops_count(self, obj):
        return obj.stops.count()


class RouteDetailSerializer(RouteListSerializer):
    stops = RouteStopSerializer(many=True, read_only=True)
    copied_from = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(RouteListSerializer.Meta):
        fields = list(RouteListSerializer.Meta.fields) + ['stops', 'copied_from']
        read_only_fields = fields


class RouteWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        from .models import Route
        model = Route
        fields = [
            'title', 'description', 'visibility',
            'tags', 'cover_photo', 'estimated_duration_minutes',
        ]
