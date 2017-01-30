
MESSAGE_RX = (
    r"^(?P<who>[a-zA-Z0-9.]+) (?P<action>created|abandoned) "
    r"(an object: )?(?P<code>D[0-9]+): (?P<description>.*)\.$"
)

