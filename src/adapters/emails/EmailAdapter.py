import re

from abc import ABC, abstractmethod

class EmailAdapter(ABC):
    @abstractmethod
    def is_disabled(self):
        pass

    @abstractmethod
    def send(self, email):
        pass

    def dedupe_recipients(self, email):
        """Split/trim `to`, `cc`, `bcc` (string or list) into deduped lists,
        then drop addresses from `cc`/`bcc` already present with higher
        priority (to > cc > bcc), since providers like Sendgrid reject
        duplicate addresses across a single send."""
        def normalize(value):
            parts = value if isinstance(value, list) else re.split(r"[;,]", str(value)) if value is not None else []
            deduped = []
            seen = set()
            for part in parts:
                address = part.strip()
                key = address.lower()
                if not address or key in seen:
                    continue
                seen.add(key)
                deduped.append(address)
            return deduped

        to = normalize(email.get('to'))
        cc = normalize(email.get('cc'))
        bcc = normalize(email.get('bcc'))

        to_seen = {address.lower() for address in to}
        cc = [address for address in cc if address.lower() not in to_seen]

        cc_seen = to_seen | {address.lower() for address in cc}
        bcc = [address for address in bcc if address.lower() not in cc_seen]

        email = dict(email)
        email['to'] = to

        if cc:
            email['cc'] = cc
        else:
            email.pop('cc', None)

        if bcc:
            email['bcc'] = bcc
        else:
            email.pop('bcc', None)

        return email
