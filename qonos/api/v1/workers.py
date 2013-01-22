import webob.exc

from qonos.common import exception
from qonos.common import utils
import qonos.db
from qonos.openstack.common import cfg
from qonos.openstack.common import wsgi
from qonos.openstack.common.gettextutils import _


CONF=cfg.CONF


class WorkersController(object):

    def __init__(self, db_api=None):
        self.db_api = db_api or qonos.db.get_api()

    def _validate_limit(self, limit):
        try:
            limit = int(limit)
        except ValueError:
            msg = _("limit param must be an integer")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        if limit <= 0:
            msg = _("limit param must be positive")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        return limit

    def _get_request_params(self, request):
        params = {}
        if request.params.get('limit') is not None:
            params['limit'] = request.params.get('limit')

        if request.params.get('marker') is not None:
            params['marker'] = request.params['marker']

        return params

    def list(self, request):
        params = {}
        params = self._get_request_params(request)
        if params.get('limit'):
            limit = params['limit']
            limit = self._validate_limit(limit)
            limit = min(CONF.api_limit_max, limit)
            params['limit'] = limit
        else:
            limit = CONF.limit_param_default
            limit = self._validate_limit(limit)
            limit = min(CONF.api_limit_max, limit)
            params['limit'] = limit
        try:
            workers = self.db_api.worker_get_all(params)
        except exception.NotFound:
            raise webob.exc.HTTPNotFound()
        [utils.serialize_datetimes(worker) for worker in workers]
        return {'workers': workers}

    def create(self, request, body):
        worker = self.db_api.worker_create(body.get('worker'))
        utils.serialize_datetimes(worker)
        return {'worker': worker}

    def get(self, request, worker_id):
        try:
            worker = self.db_api.worker_get_by_id(worker_id)
        except exception.NotFound:
            msg = _('Worker %s could not be found.') % worker_id
            raise webob.exc.HTTPNotFound(explanation=msg)
        utils.serialize_datetimes(worker)
        return {'worker': worker}

    def delete(self, request, worker_id):
        try:
            self.db_api.worker_delete(worker_id)
        except exception.NotFound:
            msg = _('Worker %s could not be found.') % worker_id
            raise webob.exc.HTTPNotFound(explanation=msg)

    def get_next_job(self, request, worker_id, body):
        action = body.get('action')
        try:
            return self.db_api.job_get_and_assign_next_by_action(action,
                                                                 worker_id)
        except exception.NotFound as e:
            msg = _('No available jobs found for action %s') % action
            raise webob.exc.HTTPNotFound(explanation=msg)


def create_resource():
    """QonoS resource factory method"""
    return wsgi.Resource(WorkersController())
