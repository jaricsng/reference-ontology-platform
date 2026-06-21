package hospital.authz

# Dynamic per-object security for the hospital platform (Module 3).
#
# The API asks: "can this user view beds, and if so, scoped to which ward?"
# This policy answers with { allow, ward_filter } where an empty ward_filter
# means "no restriction" (all wards). Roles + ward assignments live in
# data.json — policy and data are external to the application code.
#
# Roles:
#   bed_manager  -> sees all wards (ward_filter "")
#   ward_nurse   -> sees only their own assigned ward
#                   (and is denied if they explicitly request another ward)

import rego.v1

# Deny by default — unknown users / roles fall through to this.
default decision := {"allow": false, "ward_filter": ""}

subject := data.users[input.user]

# Bed managers: full visibility.
decision := {"allow": true, "ward_filter": ""} if {
	subject.role == "bed_manager"
}

# Ward nurses: scoped to their own ward, unless they ask for a different one.
decision := {"allow": true, "ward_filter": subject.ward} if {
	subject.role == "ward_nurse"
	not requesting_other_ward
}

# True when a ward was explicitly requested and it isn't the nurse's own ward.
requesting_other_ward if {
	input.ward != ""
	input.ward != subject.ward
}
