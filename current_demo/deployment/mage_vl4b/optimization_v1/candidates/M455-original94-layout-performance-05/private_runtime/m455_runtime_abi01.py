"""Pure dense contract conversion; input/weights/math remain bit-identical."""
import copy
from m455_dense_output import ABI, BUILD_ID, dense_contract


def convert_chain(original):
    if 'output_abi' in original or 'expected_build_id' in original:
        raise ValueError('Only an unmodified legacy output contract can be converted')
    result = dense_contract(original)
    if 'output_words64' in original:
        if type(original['output_words64']) is not int or original['output_words64'] * 8 != original['output_bytes']:
            raise ValueError('Legacy output word count differs')
    result['output_words64'] = result['output_bytes'] // 8
    for prior, descriptor in zip(original['descriptors'], result['descriptors']):
        if 'output_words64' in prior:
            if type(prior['output_words64']) is not int or prior['output_words64'] * 8 != prior['output_bytes']:
                raise ValueError('Legacy descriptor output word count differs')
            descriptor['output_words64'] = descriptor['output_bytes'] // 8
    return result


def convert_contract_payload(original):
    chains = original.get('chains')
    if not isinstance(chains, list) or not chains:
        raise ValueError('Original validated contract has no chains')
    if any(type(c.get('chain_index')) is not int or c['chain_index'] != i for i, c in enumerate(chains)):
        raise ValueError('Original chain ordering differs')
    result = copy.deepcopy(original)
    result['chains'] = [convert_chain(c) for c in chains]
    result['output_abi'] = ABI
    result['expected_build_id'] = BUILD_ID
    return result
