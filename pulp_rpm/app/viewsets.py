from gettext import gettext as _  # noqa:F401

from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import detail_route

from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositoryPublishURLSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.viewsets import (
    BaseFilterSet,
    ContentViewSet,
    RemoteViewSet,
    OperationPostponedResponse,
    PublisherViewSet
)

from pulp_rpm.app import tasks
from pulp_rpm.app.models import Package, RpmRemote, RpmPublisher, UpdateRecord
from pulp_rpm.app.serializers import (
    MinimalPackageSerializer,
    PackageSerializer,
    RpmRemoteSerializer,
    RpmPublisherSerializer,
    UpdateRecordSerializer,
    MinimalUpdateRecordSerializer
)


class PackageFilter(BaseFilterSet):
    """
    FilterSet for Package.
    """

    class Meta:
        model = Package
        fields = {
            'name': ['exact', 'in'],
            'epoch': ['exact', 'in'],
            'version': ['exact', 'in'],
            'release': ['exact', 'in'],
            'arch': ['exact', 'in'],
            'pkgId': ['exact', 'in'],
            'checksum_type': ['exact', 'in'],
        }


class PackageViewSet(ContentViewSet):
    """
    A ViewSet for Package.

    Define endpoint name which will appear in the API endpoint for this content type.
    For example::
        http://pulp.example.com/pulp/api/v3/content/rpm/packages/

    Also specify queryset and serializer for Package.
    """

    endpoint_name = 'rpm/packages'
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    minimal_serializer_class = MinimalPackageSerializer
    filterset_class = PackageFilter


class RpmRemoteViewSet(RemoteViewSet):
    """
    A ViewSet for RpmRemote.
    """

    endpoint_name = 'rpm'
    queryset = RpmRemote.objects.all()
    serializer_class = RpmRemoteSerializer

    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to sync RPM content.",
        responses={202: AsyncOperationResponseSerializer}
    )
    @detail_route(methods=('post',), serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Dispatches a sync task.
        """
        remote = self.get_object()
        serializer = RepositorySyncURLSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        repository = serializer.validated_data.get('repository')

        result = enqueue_with_reservation(
            tasks.synchronize,
            [repository, remote],
            kwargs={
                'remote_pk': remote.pk,
                'repository_pk': repository.pk
            }
        )
        return OperationPostponedResponse(result, request)


class RpmPublisherViewSet(PublisherViewSet):
    """
    A ViewSet for RpmPublisher.
    """

    endpoint_name = 'rpm'
    queryset = RpmPublisher.objects.all()
    serializer_class = RpmPublisherSerializer

    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to publish RPM content.",
        responses={202: AsyncOperationResponseSerializer}
    )
    @detail_route(methods=('post',), serializer_class=RepositoryPublishURLSerializer)
    def publish(self, request, pk):
        """
        Dispatches a publish task.
        """
        publisher = self.get_object()
        serializer = RepositoryPublishURLSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        repository_version = serializer.validated_data.get('repository_version')

        # Safe because version OR repository is enforced by serializer.
        if not repository_version:
            repository = serializer.validated_data.get('repository')
            repository_version = RepositoryVersion.latest(repository)

        result = enqueue_with_reservation(
            tasks.publish,
            [repository_version.repository, publisher],
            kwargs={
                'publisher_pk': publisher.pk,
                'repository_version_pk': repository_version.pk
            }
        )
        return OperationPostponedResponse(result, request)


class UpdateRecordFilter(BaseFilterSet):
    """
    FilterSet for UpdateRecord.
    """

    class Meta:
        model = UpdateRecord
        fields = {
            'errata_id': ['exact', 'in'],
            'status': ['exact', 'in'],
            'severity': ['exact', 'in'],
            'update_type': ['exact', 'in'],
        }


class UpdateRecordViewSet(ContentViewSet):
    """
    A ViewSet for UpdateRecord.

    Define endpoint name which will appear in the API endpoint for this content type.
    For example::
        http://pulp.example.com/pulp/api/v3/content/rpm/errata/

    Also specify queryset and serializer for UpdateRecord.
    """

    endpoint_name = 'rpm/errata'
    queryset = UpdateRecord.objects.all()
    serializer_class = UpdateRecordSerializer
    minimal_serializer_class = MinimalUpdateRecordSerializer
    filterset_class = UpdateRecordFilter
