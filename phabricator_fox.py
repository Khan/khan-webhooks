
MESSAGE_RX = (
    r"^(?P<who>[a-zA-Z0-9.]+) "
    r"(?P<action>requested review of) "
    r"(an object: )?(?P<code>D[0-9]+): (?P<description>.*)\.$"
)
