def handler(event, _):
    number = event['number']
    return dict(number=number * 2)
