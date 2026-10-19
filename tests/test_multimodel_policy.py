"""Stdlib tests for the design-only managed Jetson peer policy."""
import unittest

from jetlink.multimodel_policy import (
    CAPABILITY,
    PeerPolicyError,
    is_managed_jetson_peer,
    loaded_sha,
    selection_kind,
)


SHA = "c" * 64


def peer(**changes):
    value = {
        "protocol": 3,
        "carrot_host": "jetson",
        "backend": "trt",
        "device": "Orin-sm87",
        CAPABILITY: {"version": 1, "selection": "host"},
        "loaded": SHA,
    }
    value.update(changes)
    return value


class ManagedJetsonPolicyTest(unittest.TestCase):
    def test_exact_contract_is_managed(self):
        self.assertTrue(is_managed_jetson_peer(peer()))
        self.assertEqual(loaded_sha(peer()), SHA)
        self.assertEqual(selection_kind(peer()), "managed-jetson")

    def test_no_loaded_model_is_waiting_not_invalid(self):
        self.assertIsNone(loaded_sha(peer(loaded=None)))

    def test_legacy_jetson_stays_legacy(self):
        value = peer()
        value.pop(CAPABILITY)
        self.assertFalse(is_managed_jetson_peer(value))
        self.assertEqual(selection_kind(value), "legacy-jetson")

    def test_protocol2_never_opts_in(self):
        self.assertFalse(is_managed_jetson_peer(peer(protocol=2)))
        self.assertEqual(selection_kind(peer(protocol=2)), "legacy-jetson")

    def test_only_usb_path_is_allowed(self):
        self.assertTrue(is_managed_jetson_peer(peer(), "usb"))
        self.assertFalse(is_managed_jetson_peer(peer(), "auto"))
        self.assertFalse(is_managed_jetson_peer(peer(), "ios"))
        self.assertFalse(is_managed_jetson_peer(peer(), "android"))

    def test_host_and_backend_are_explicit(self):
        self.assertFalse(is_managed_jetson_peer(peer(carrot_host="mac")))
        self.assertFalse(is_managed_jetson_peer(peer(backend="ort")))
        self.assertFalse(is_managed_jetson_peer(peer(device="")))

    def test_capability_is_versioned_and_exact(self):
        self.assertFalse(is_managed_jetson_peer(peer(**{CAPABILITY: True})))
        self.assertFalse(is_managed_jetson_peer(
            peer(**{CAPABILITY: {"version": 2, "selection": "host"}})))
        self.assertFalse(is_managed_jetson_peer(
            peer(**{CAPABILITY: {"version": 1, "selection": "comma"}})))
        self.assertFalse(is_managed_jetson_peer(
            peer(**{CAPABILITY: {"version": 1, "selection": "host", "extra": True}})))

    def test_invalid_loaded_identity_fails_closed(self):
        for value in ("C" * 64, "abc", "../model", 7, True, ""):
            with self.subTest(value=value):
                with self.assertRaises(PeerPolicyError):
                    loaded_sha(peer(loaded=value))

    def test_nonmanaged_peer_cannot_supply_loaded_identity(self):
        value = peer()
        value.pop(CAPABILITY)
        with self.assertRaises(PeerPolicyError):
            loaded_sha(value)


if __name__ == "__main__":
    unittest.main()
