"""Qiskit circuits for the same Grover operator as estimation.py.

Powers of Q are appended one application at a time, with a barrier between
applications, so the transpiler cannot replace Q^m by a single rotation.
That fused rotation is a different experiment: it classically computes the
power and does not implement the oracle-call sequence.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate, StatePreparation, UnitaryGate

import estimation


def preparation_and_grover(theta: float) -> tuple[np.ndarray, np.ndarray, float]:
    preparation = estimation.ry_preparation(theta)
    state = preparation[:, 0]
    operator = estimation.grover_from_state(state)
    amplitude = float(np.sin(theta) ** 2)
    return preparation, operator, amplitude


def amplification_circuit(theta: float, repetitions: int) -> QuantumCircuit:
    """A followed by `repetitions` applications of Q, then a measurement of the marked bit."""
    if repetitions < 0:
        raise ValueError("repetitions must be nonnegative")
    preparation, operator, _ = preparation_and_grover(theta)
    circuit = QuantumCircuit(1, 1, name=f"amp_m{repetitions}")
    circuit.unitary(preparation, [0], label="A")
    grover = UnitaryGate(operator, label="Q")
    for _ in range(repetitions):
        circuit.barrier()
        circuit.append(grover, [0])
    circuit.measure(0, 0)
    return circuit


def canonical_ae_circuit(theta: float, phase_bits: int) -> QuantumCircuit:
    """Phase estimation of Q. Phase qubit k controls 2^k separate applications of Q.

    Phase qubit 0 is the least-significant bit of the bin index. The system
    qubit is the last qubit and is not measured.
    """
    if phase_bits < 1:
        raise ValueError("phase_bits must be at least 1")
    preparation, operator, _ = preparation_and_grover(theta)
    system = phase_bits
    circuit = QuantumCircuit(phase_bits + 1, phase_bits, name=f"qpe_m{phase_bits}")
    circuit.unitary(preparation, [system], label="A")
    for qubit in range(phase_bits):
        circuit.h(qubit)
    controlled = UnitaryGate(operator, label="Q").control(1)
    for bit in range(phase_bits):
        for _ in range(1 << bit):
            circuit.barrier()
            circuit.append(controlled, [bit, system])
    circuit.append(QFTGate(phase_bits).inverse(), range(phase_bits))
    circuit.measure(range(phase_bits), range(phase_bits))
    return circuit


def call_loader_circuit(state: np.ndarray) -> QuantumCircuit:
    """Prepare the call-grid state and measure the marked (least-significant) qubit."""
    vector = np.asarray(state, dtype=complex).reshape(-1)
    n_qubits = int(np.log2(vector.size))
    if 1 << n_qubits != vector.size:
        raise ValueError("state length is not a power of two")
    circuit = QuantumCircuit(n_qubits, 1, name="call_loader")
    circuit.append(StatePreparation(vector), range(n_qubits))
    circuit.measure(0, 0)
    return circuit
