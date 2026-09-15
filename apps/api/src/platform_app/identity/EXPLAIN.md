# Entscheidungen und Datenfluss

Browser → /auth/login → kurzlebiger verschlüsselter PKCE-Datensatz → Keycloak → /auth/callback → JWT-Prüfung → opaque Sitzungscookies. Der Auth-Datenbankzugang liest Identitäten und Sessions; die Anwendungsrolle liest sie nicht. Jeder Fachrequest prüft Ablauf, auth_epoch, aktuelle Mitgliedschaft und Rollen erneut. Mutationen prüfen zusätzlich Origin und CSRF. Rollenänderungen nehmen denselben Organisationslock wie Fachmutationen.

## Ausfälle und Grenzen

Ungültige, abgelaufene oder bereits verbrauchte Loginversuche werden verworfen. Provideradressen dürfen nur zum konfigurierten Issuer gehören; JWTs brauchen RS256, einen eindeutigen passenden RSA-Schlüssel und gültige Zeit-/Audience-/Nonce-Werte. OIDC-/DB-Ausfälle liefern deutsche Fehler ohne Token oder Providerdaten im Log.

## Erweiterung

Neue Rollen benötigen serverseitige Berechtigungen, RLS-/API-Negativtests und aktualisierte UI-Anzeige. Produktive IdP-Provisionierung und TLS-Konfiguration sind getrennte Betriebsaufgaben. Eine fremde Rolle aus einem ID-Token darf nie zur lokalen Freigabe werden.
