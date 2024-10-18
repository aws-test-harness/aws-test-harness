def handler(event, _):
    number = event.get('data')['number']
    return dict(number=number + 1)
