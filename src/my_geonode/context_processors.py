import os 

def export_vars(request):
    data = {}
    data['APP_ENV'] = os.environ['APP_ENV']
    return data