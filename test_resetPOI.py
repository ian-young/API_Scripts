import resetPOI as reset
import json


def test_getPeople():
    expected = [{'created': 1698183283, 'label': 'PoI9', 'last_seen': 0, 'person_id': '8d2cff6c-8ad6-4e3c-a828-c9d6692c6403'}, {'created': 1698183280, 'label': 'PoI8', 'last_seen': 0, 'person_id': '5d848fde-d0ed-4c76-b850-1385d8e91286'}, {'created': 1698183277, 'label': 'PoI7', 'last_seen': 0, 'person_id': '8ef774c1-8f54-4503-937e-8e64d358840b'}, {'created': 1698183273, 'label': 'PoI6', 'last_seen': 0, 'person_id': '308d49fb-0bfb-41d2-88fa-d5b84522643c'}, {'created': 1698183270, 'label': 'PoI5', 'last_seen': 0, 'person_id': '592984ed-c762-4e0a-9f78-aba4b08cc418'}, {'created': 1698183269, 'label': 'PoI4', 'last_seen': 0,
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            'person_id': '0830f887-48bb-4ddd-8029-9dd2bcf56c31'}, {'created': 1698183266, 'label': 'PoI3', 'last_seen': 0, 'person_id': '3ef41069-cc59-48af-999f-ef5993ca2ecb'}, {'created': 1698183264, 'label': 'PoI2', 'last_seen': 0, 'person_id': 'b1182cbc-a273-46c7-a96f-afdd6dc3a181'}, {'created': 1698183285, 'label': 'PoI10', 'last_seen': 0, 'person_id': 'f4d81c75-8ac1-4d6e-b01b-684198884bda'}, {'created': 1698183262, 'label': 'PoI1', 'last_seen': 0, 'person_id': '44cc9622-e513-4bed-8ac2-73a04f184c22'}, {'created': 1696861526, 'label': 'PoI', 'last_seen': 0, 'person_id': '19895ed5-b8d4-400a-b4bb-9f0787cf4c8c'}]
    people = reset.getPeople()
    assert people == expected


def test_getPOI():
    people = reset.getPeople()
    labels = reset.getIds(people)
    print(labels)
    assert labels == ['8d2cff6c-8ad6-4e3c-a828-c9d6692c6403', '5d848fde-d0ed-4c76-b850-1385d8e91286', '8ef774c1-8f54-4503-937e-8e64d358840b', '308d49fb-0bfb-41d2-88fa-d5b84522643c', '592984ed-c762-4e0a-9f78-aba4b08cc418',
                      '0830f887-48bb-4ddd-8029-9dd2bcf56c31', '3ef41069-cc59-48af-999f-ef5993ca2ecb', 'b1182cbc-a273-46c7-a96f-afdd6dc3a181', 'f4d81c75-8ac1-4d6e-b01b-684198884bda', '44cc9622-e513-4bed-8ac2-73a04f184c22', '19895ed5-b8d4-400a-b4bb-9f0787cf4c8c']


def test_getId():
    assert reset.getPersonId(
        'PoI', reset.getPeople()) == '19895ed5-b8d4-400a-b4bb-9f0787cf4c8c'


def test_getName():
    assert reset.printName(
        '19895ed5-b8d4-400a-b4bb-9f0787cf4c8c', reset.getPeople()) == 'PoI'


def test_cleanList():
    live_list = [1, 2, 3, None, None, 4]
    compare_list = [1, 2, 3, 4]

    live_list = reset.cleanList(live_list)

    assert live_list == compare_list
