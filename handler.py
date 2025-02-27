"""Service entry-point."""
import json
import logging

from service.dal import Project
from service.models import JSONManifest, JSONFactory


# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Lambda entry
def main(event, context=None):  # pylint: disable=unused-argument
    """Handle loandata as Eventbridge event and return report.

    The reports generated by the service have the following envelope:

    ```json
    {
        "reports": [
            {
                "title": "<the report title>",
                ...
            },
            ...
        ]
    }
    ```

    Parameters
    ----------
    event : dict
        The Eventbridge event payload with loandata for reporting as its detail.
    context : LambdaContext
        The lambda context object (for Lambda use only).

    Returns
    -------
    dict{str:any}
        Returns a dict which contains the reports generated by the service.

    """
    event = {} if event is None else event
    logger.info('Service invoked by event: %s', json.dumps(event, indent=2))

    # Load all rules
    project = Project()
    rules = [rule for _ in project.resources.values() for rule in _]
    logger.info('Service loaded rules: %s', json.dumps(rules, indent=2))

    # Confirm event is valid EventBridge -> SQS payload
    loans = []
    for record in event.get('Records', [{}]):
        if not all(
            key in record for key in ['source', 'detail-type', 'detail']
        ):
            logger.error(
                'Service received invalid EventBridge event- Skipping event'
            )
            continue

        # Attempt to load loandata
        try:
            loans.append(json.loads(record['detail']))
        except json.JSONDecodeError:
            logger.error(
                'Service received invalid event detail- Skipping event'
            )
            continue

    logger.info('Service recieved loans: %s', json.dumps(loans, indent=2))

    # Generate Manifests
    reports = []
    for loan in loans:
        manifest = JSONManifest(loan, rules)
        logger.info(
            'Generated manifest: %s', json.dumps(manifest.items, indent=2)
        )

        projection = JSONFactory(manifest).get_projection()
        logger.info(
            'Generated projection: %s', json.dumps(projection, indent=2)
        )
        reports.extend(projection.get('reports', []))

        # Check to make sure both reports populated
        if len(reports) == 2:
            all_residences = len(reports[1].get('residences', []))

            # Convert dicts to json strings
            # Convert to set to remove redundant json strings then back to list
            json_str_list = list(set([json.dumps(r) for r in reports[1].get('residences', [])]))

            # If redundant residences were removed, then borrower and coborrower share an address
            reports[0]['shared_address'] = True if all_residences > len(json_str_list) else False

            # Convert back to dicts and assign to residences
            reports[1]['residences'] = [json.loads(r) for r in json_str_list]

    # Reformat report output and return
    return {'reports': reports}
