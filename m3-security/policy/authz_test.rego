package hospital.authz_test

import data.hospital.authz

import rego.v1

users := {"users": {
	"manager_carol": {"role": "bed_manager"},
	"nurse_alice": {"role": "ward_nurse", "ward": "Ward A"},
}}

test_bed_manager_sees_all if {
	d := authz.decision with input as {"user": "manager_carol", "ward": ""}
		with data.users as users.users
	d == {"allow": true, "ward_filter": ""}
}

test_ward_nurse_scoped_to_own_ward if {
	d := authz.decision with input as {"user": "nurse_alice", "ward": ""}
		with data.users as users.users
	d == {"allow": true, "ward_filter": "Ward A"}
}

test_ward_nurse_own_ward_request_allowed if {
	d := authz.decision with input as {"user": "nurse_alice", "ward": "Ward A"}
		with data.users as users.users
	d.allow == true
}

test_ward_nurse_other_ward_denied if {
	d := authz.decision with input as {"user": "nurse_alice", "ward": "ICU"}
		with data.users as users.users
	d.allow == false
}

test_unknown_user_denied if {
	d := authz.decision with input as {"user": "intruder", "ward": ""}
		with data.users as users.users
	d.allow == false
}
