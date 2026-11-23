from flet_visual_builder.catalogue import catalogue


def test_sequence_codec_rejects_mutable_lists_outside_frozen_document_contract():
    assert catalogue.codecs["dropdown_options"].validate([{"text": "A"}])
    assert not catalogue.codecs["dropdown_options"].validate(({"text": "A"},))
