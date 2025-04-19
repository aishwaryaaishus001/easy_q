from django.contrib import admin
from .models import Question, ClusteredQuestion
from django.db.models import Count
from django.utils.html import format_html

# Register your models here.

admin.site.register(Question)

@admin.register(ClusteredQuestion)
class ClusteredQuestionAdmin(admin.ModelAdmin):
    list_display = ('paper', 'text', 'module', 'cluster_label', 'difficulty')  # Show paper, text, module, cluster, and difficulty
    list_filter = ('paper', 'cluster_label', 'difficulty')  # Filters to view by paper, cluster, and difficulty
    search_fields = ('text', 'module', 'paper')  # Allow searching by text, module, or paper
    ordering = ('paper', 'cluster_label')  # Order by paper and cluster

    def changelist_view(self, request, extra_context=None):
        # Aggregate cluster counts per paper
        cluster_summary = (
            ClusteredQuestion.objects
            .values('paper', 'cluster_label')
            .annotate(count=Count('id'))
            .order_by('paper', 'cluster_label')
        )

        # Organize cluster counts by paper: {paper: {cluster_label: count}}
        summary_dict = {}
        for entry in cluster_summary:
            paper = entry['paper']
            label = entry['cluster_label']
            count = entry['count']
            summary_dict.setdefault(paper, {})[label] = count

        # Add the summary to the admin context for display in the changelist view
        extra_context = extra_context or {}
        extra_context['cluster_summary'] = summary_dict

        return super().changelist_view(request, extra_context=extra_context)

    def cluster_summary_display(self, obj):
        # Display paper-wise cluster distribution in the admin list
        summary = self.cluster_summary.get(obj.paper, {})
        cluster_0 = summary.get(0, 0)
        cluster_1 = summary.get(1, 0)
        cluster_2 = summary.get(2, 0)
        return format_html(
            "<strong>Cluster 0:</strong> {0} <br> <strong>Cluster 1:</strong> {1} <br> <strong>Cluster 2:</strong> {2}",
            cluster_0, cluster_1, cluster_2
        )

    cluster_summary_display.short_description = 'Cluster Distribution'
