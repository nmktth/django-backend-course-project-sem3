from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from simple_history.admin import SimpleHistoryAdmin

from .models import Album, Photo, Collage, BugReport
from .utils import export_queryset_to_excel


class AlbumResource(resources.ModelResource):
    photo_count = fields.Field()

    class Meta:
        model = Album
        fields = ("id", "title", "user__username", "is_public", "created_at", "photo_count")
        export_order = ("id", "title", "user__username", "created_at", "is_public", "photo_count")

    def dehydrate_is_public(self, album):
        return "Public" if album.is_public else "Private"

    def dehydrate_photo_count(self, album):
        return album.photos.count()

    def get_export_queryset(self, request, queryset):
        return queryset.order_by("-created_at")


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1
    readonly_fields = ("created_at",)


@admin.register(Album)
class AlbumAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = AlbumResource
    list_display = ("title", "user", "is_public", "photo_count", "created_at")
    list_display_links = ("title",)
    list_filter = ("is_public", "created_at", "user")
    search_fields = ("title", "description")
    ordering = ("-created_at",)
    inlines = [PhotoInline]
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user",)
    filter_horizontal = ("editors",)

    fieldsets = (
        ("Основные", {
            "fields": ("title", "description", "user")
        }),
        ("Настройки", {
            "fields": ("is_public", "editors")
        }),
        ("Даты", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    @admin.display(description="Фотографии")
    def photo_count(self, obj):
        return obj.photos.count()


@admin.register(BugReport)
class BugReportAdmin(ImportExportModelAdmin):
    list_display = ("title", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description", "user__username")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
    raw_id_fields = ("user",)
    actions = ["export_to_excel"]

    @admin.action(description="Экспорт выбранных баг-репортов в Excel (Custom)")
    def export_to_excel(self, request, queryset):
        headers = ["ID", "User", "Title", "Description", "Status", "Created At"]

        def extract_row(report):
            return [
                report.id,
                report.user.username if report.user else "Anonymous",
                report.title,
                report.description,
                report.status,
                report.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]

        return export_queryset_to_excel(
            queryset=queryset,
            headers=headers,
            row_extractor=extract_row,
            sheet_title="Bug Reports",
            filename_prefix="bug_reports",
        )


@admin.register(Photo)
class PhotoAdmin(SimpleHistoryAdmin):
    list_display = ("id", "album", "created_at", "is_favorite")
    list_filter = ("created_at", "is_favorite", "album__user")
    search_fields = ("album__title", "public_token")
    raw_id_fields = ("album",)
    date_hierarchy = "created_at"


admin.site.register(Collage)
