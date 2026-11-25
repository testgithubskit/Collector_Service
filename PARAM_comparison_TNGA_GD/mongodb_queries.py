
def search_parameter(parameter):
    return [
            {
                '$match': {
                    'signalname': parameter
                }
            }, {
                '$project': {
                    '_id': 0,
                    'updatedate': 1,
                    'value': 1
                }
            }, {
                '$limit': 1
            }
    ]
