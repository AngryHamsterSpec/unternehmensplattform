# Identität und Organisationsrechte

Das Modul führt den OIDC-Codefluss mit PKCE, State, Nonce und serverseitigen Sessions aus. Die Identität wird über issuer und sub gebunden; Rollen kommen ausschließlich aus lokalen Mitgliedschaften. Eine Person wählt nach dem Login ihren Organisationskontext. Organisation wechseln und Logout widerrufen das alte Sitzungstoken. Mitgliedschaften lassen sich mit Revisionsprüfung ändern; die letzte aktive Administration bleibt geschützt.

Browser → /auth/login → kurzlebiger verschlüsselter PKCE-Datensatz → Keycloak → /auth/callback → JWT-Prüfung → opaque Sitzungscookies. Der Auth-Datenbankzugang liest Identitäten und Sessions; die Anwendungsrolle liest sie nicht. Jeder Fachrequest prüft Ablauf, auth_epoch, aktuelle Mitgliedschaft und Rollen erneut. Mutationen prüfen zusätzlich Origin und CSRF. Rollenänderungen nehmen denselben Organisationslock wie Fachmutationen.

Siehe [Erklärung](EXPLAIN.md), [Prüfung](TESTING.md) und den [aktuellen Projektstatus](../../../../../docs/STATUS.md).
