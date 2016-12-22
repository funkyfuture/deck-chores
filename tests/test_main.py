from pytest import mark

from deck_chores.main import listen, there_is_another_deck_chores_container
from deck_chores.parsers import _parse_job_defintion


_events = b'''{"status":"rename","id":"a84c8e16c1b1b2339bd276f725f08425935c51a5d2c68c5d28ec786c68155830","from":"sojus_beep","Type":"container","Action":"rename","Actor":{"ID":"a84c8e16c1b1b2339bd276f725f08425935c51a5d2c68c5d28ec786c68155830","Attributes":{"com.docker.compose.config-hash":"1319acc48e2ae136c2728263c594ddcf874dc7d1ea906236080ea6b37dc1851f","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"a84c8e16c1b1_sojus_beep_1","oldName":"/sojus_beep_1"}},"time":1481662806,"timeNano":1481662806327986727}\n
{"status":"create","id":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","from":"sojus_beep","Type":"container","Action":"create","Actor":{"ID":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","Attributes":{"com.docker.compose.config-hash":"e3d91116d5749958cb37be661e8e7717c9303c16fec89112753b645db4c960c6","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"sojus_beep_1"}},"time":1481662807,"timeNano":1481662807469639050}\n
{"Type":"network","Action":"disconnect","Actor":{"ID":"f3f85b06a56107f4358538d554df5ba0664f43e553585c66e5d4c0646daf752b","Attributes":{"container":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","name":"sojus_default","type":"bridge"}},"time":1481662807,"timeNano":1481662807584951463}\n
{"Type":"network","Action":"connect","Actor":{"ID":"f3f85b06a56107f4358538d554df5ba0664f43e553585c66e5d4c0646daf752b","Attributes":{"container":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","name":"sojus_default","type":"bridge"}},"time":1481662807,"timeNano":1481662807944818738}\n
{"status":"start","id":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","from":"sojus_beep","Type":"container","Action":"start","Actor":{"ID":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","Attributes":{"com.docker.compose.config-hash":"e3d91116d5749958cb37be661e8e7717c9303c16fec89112753b645db4c960c6","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"sojus_beep_1"}},"time":1481662808,"timeNano":1481662808694670749}\n
{"status":"destroy","id":"a84c8e16c1b1b2339bd276f725f08425935c51a5d2c68c5d28ec786c68155830","from":"sojus_beep","Type":"container","Action":"destroy","Actor":{"ID":"a84c8e16c1b1b2339bd276f725f08425935c51a5d2c68c5d28ec786c68155830","Attributes":{"com.docker.compose.config-hash":"1319acc48e2ae136c2728263c594ddcf874dc7d1ea906236080ea6b37dc1851f","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"a84c8e16c1b1_sojus_beep_1"}},"time":1481662808,"timeNano":1481662808774228540}\n
{"status":"pause","id":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","from":"sojus_beep","Type":"container","Action":"pause","Actor":{"ID":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","Attributes":{"com.docker.compose.config-hash":"e3d91116d5749958cb37be661e8e7717c9303c16fec89112753b645db4c960c6","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"sojus_beep_1"}},"time":1481662814,"timeNano":1481662814240938618}\n
{"status":"unpause","id":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","from":"sojus_beep","Type":"container","Action":"unpause","Actor":{"ID":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","Attributes":{"com.docker.compose.config-hash":"e3d91116d5749958cb37be661e8e7717c9303c16fec89112753b645db4c960c6","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"sojus_beep_1"}},"time":1481662817,"timeNano":1481662817234268429}\n
{"status":"kill","id":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","from":"sojus_beep","Type":"container","Action":"kill","Actor":{"ID":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","Attributes":{"com.docker.compose.config-hash":"e3d91116d5749958cb37be661e8e7717c9303c16fec89112753b645db4c960c6","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"sojus_beep_1","signal":"15"}},"time":1481662822,"timeNano":1481662822612737795}\n
{"status":"kill","id":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","from":"sojus_beep","Type":"container","Action":"kill","Actor":{"ID":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","Attributes":{"com.docker.compose.config-hash":"e3d91116d5749958cb37be661e8e7717c9303c16fec89112753b645db4c960c6","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"sojus_beep_1","signal":"9"}},"time":1481662832,"timeNano":1481662832614494260}\n
{"status":"die","id":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","from":"sojus_beep","Type":"container","Action":"die","Actor":{"ID":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","Attributes":{"com.docker.compose.config-hash":"e3d91116d5749958cb37be661e8e7717c9303c16fec89112753b645db4c960c6","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","exitCode":"137","image":"sojus_beep","name":"sojus_beep_1"}},"time":1481662832,"timeNano":1481662832668193924}\n
{"Type":"network","Action":"disconnect","Actor":{"ID":"f3f85b06a56107f4358538d554df5ba0664f43e553585c66e5d4c0646daf752b","Attributes":{"container":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","name":"sojus_default","type":"bridge"}},"time":1481662833,"timeNano":1481662833259012276}\n
{"status":"stop","id":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","from":"sojus_beep","Type":"container","Action":"stop","Actor":{"ID":"8c0ea93ef7145750d2a39b893977500810f065ccbf004b41ebd30b2224778d58","Attributes":{"com.docker.compose.config-hash":"e3d91116d5749958cb37be661e8e7717c9303c16fec89112753b645db4c960c6","com.docker.compose.container-number":"1","com.docker.compose.oneoff":"False","com.docker.compose.project":"sojus","com.docker.compose.service":"beep","com.docker.compose.version":"1.9.0","deck-chores.beep.command":"/beep.sh","deck-chores.beep.interval":"15","image":"sojus_beep","name":"sojus_beep_1"}},"time":1481662833,"timeNano":1481662833364283106}'''  # noqa: E501


def test_event_dispatching(mocker):
    mocker.patch('deck_chores.config.Client.events',
                 return_value=(x for x in _events.splitlines() if x))
    mocker.patch('deck_chores.config.Client.inspect_container',
                 return_value={'Name': 'foo'})
    labels = mocker.patch('deck_chores.parsers.labels')
    definition = _parse_job_defintion({'deck-chores.beep.command': '/beep.sh',
                                       'deck-chores.beep.interval': '15'})
    labels.return_value = ('foo', 'service', definition)
    add = mocker.patch('deck_chores.jobs.add')
    listen()
    assert labels.call_count == 2
    assert add.call_count == 1


@mark.parametrize('has_label_seq, exp_result',
                  (([True, False, True], True),
                   ([True, False], False)))
def test_deck_chores_container_check(mocker, has_label_seq, exp_result):
    def inspect_image(self, id):
        nonlocal has_label_seq
        if has_label_seq.pop(0):
            return {'Config': {'Labels': {'org.label-schema.name': 'deck-chores'}}}
        else:
            return {'Config': {}}

    def inspect_container(self, id):
        nonlocal has_label_seq
        return {'Id': str(has_label_seq[0]), 'Image': str(has_label_seq[0])}

    mocker.patch('deck_chores.config.Client.containers',
                 return_value=[{'Id': str(x), 'State': 'running'} for x in range(len(has_label_seq))])  # noqa: E501
    mocker.patch('deck_chores.config.Client.inspect_image', inspect_image)
    mocker.patch('deck_chores.config.Client.inspect_container', inspect_container)
    assert there_is_another_deck_chores_container() == exp_result
