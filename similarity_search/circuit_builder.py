"""
Quantum Circuit Builder for similarity search.
"""

from math import asin, sqrt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


class SimilaritySearchCircuitBuilder:
    """Class for building quantum circuits for similarity search."""

    @staticmethod
    def swap_test_circuit(state1_qreg, state2_qreg, ancilla_qreg):
        """
        Constructs a SWAP test circuit between two quantum registers.
        """
        qc = QuantumCircuit(ancilla_qreg, state1_qreg, state2_qreg)

        # Apply Hadamard to ancilla
        qc.h(ancilla_qreg[0])

        # Apply controlled SWAP operations between corresponding qubits
        for i in range(len(state1_qreg)):
            qc.cswap(ancilla_qreg[0], state1_qreg[i], state2_qreg[i])

        # Apply Hadamard to ancilla again
        qc.h(ancilla_qreg[0])

        return qc

    @staticmethod
    def oracle_circuit(target_state, num_qubits, threshold):
        """
        Creates an oracle that marks states with similarity greater than threshold to target_state.
        """

        # Create registers
        oracle_reg = QuantumRegister(num_qubits, "oracle")
        target_reg = QuantumRegister(num_qubits, "target")
        ancilla_reg = QuantumRegister(1, "ancilla")
        phase_reg = QuantumRegister(1, "phase")

        # Create circuit
        qc = QuantumCircuit(oracle_reg, target_reg, ancilla_reg, phase_reg)

        # Prepare the target state in target_reg
        qc.initialize(target_state, target_reg)

        # Create and compose the SWAP test circuit
        swap_test = SimilaritySearchCircuitBuilder.swap_test_circuit(
            oracle_reg,
            target_reg,
            ancilla_reg,
        )
        qc.compose(swap_test, inplace=True)

        # Flip the ancilla to mark high similarity states
        qc.x(ancilla_reg[0])

        # Calculate angle for the rotation
        angle = asin(sqrt(threshold))

        # Apply controlled phase rotation based on similarity threshold
        qc.ch(ancilla_reg[0], phase_reg[0])  # Apply controlled-H
        qc.cp(2 * angle, ancilla_reg[0], phase_reg[0])  # Apply controlled-Phase
        qc.ch(ancilla_reg[0], phase_reg[0])  # Apply controlled-H again

        # Flip the ancilla back
        qc.x(ancilla_reg[0])

        # Uncompute the SWAP test to clean up ancilla qubits
        swap_test_dag = swap_test.inverse()
        qc.compose(swap_test_dag, inplace=True)

        # Reset all target register qubits to |0⟩ state
        for i in range(num_qubits):
            qc.reset(target_reg[i])

        return qc

    @staticmethod
    def diffuser_circuit(num_qubits):
        """
        Creates the standard diffusion operator for Grover's algorithm.

        Args:
            num_qubits (int): Number of qubits

        Returns:
            QuantumCircuit: Diffusion operator circuit
        """
        qc = QuantumCircuit(num_qubits)

        # Apply H gates to all qubits
        for i in range(num_qubits):
            qc.h(i)

        # First, apply X gates to all qubits
        for i in range(num_qubits):
            qc.x(i)

        # Apply multi-controlled Z operation
        if num_qubits == 1:
            qc.z(0)
        elif num_qubits == 2:
            qc.cz(0, 1)
        else:
            # For 3+ qubits, use multi-controlled Z pattern
            # Last qubit is target, all others are controls
            target = num_qubits - 1

            # Apply H to target
            qc.h(target)

            # Use all qubits except the target as controls in a balanced tree
            controls = list(range(num_qubits - 1))

            # Apply multi-controlled X on the target qubit
            # First level of the tree - directly connect controls to target
            for control in controls:
                qc.cx(control, target)

            # Apply H to target
            qc.h(target)

        # Uncompute X gates
        for i in range(num_qubits):
            qc.x(i)

        # Apply H gates to all qubits again
        for i in range(num_qubits):
            qc.h(i)

        return qc

    @staticmethod
    def grover_search_high_similarity(
        target_state, num_qubits, iterations=1, threshold=0.1
    ):
        """
        Implements Grover's search for states with high similarity to the target.

        Args:
            target_state (Statevector): Target state for similarity comparison
            num_qubits (int): Number of qubits
            iterations (int): Number of Grover iterations
            threshold (float): Minimum similarity threshold

        Returns:
            QuantumCircuit: Complete Grover search circuit
        """
        # Create registers for the main algorithm
        oracle_reg = QuantumRegister(num_qubits, "oracle")
        target_reg = QuantumRegister(num_qubits, "target")
        ancilla_reg = QuantumRegister(1, "ancilla")
        phase_reg = QuantumRegister(1, "phase")
        cr = ClassicalRegister(num_qubits, "c")

        # Create a circuit with all necessary registers
        grover_circuit = QuantumCircuit(
            oracle_reg, target_reg, ancilla_reg, phase_reg, cr
        )

        # Initialize with Hadamard on the oracle register (search space)
        for i in range(num_qubits):
            grover_circuit.h(oracle_reg[i])

        # Get the oracle for high similarity
        oracle = SimilaritySearchCircuitBuilder.oracle_circuit(
            target_state, num_qubits, threshold
        )

        # Get the diffusion operator
        diffusion = SimilaritySearchCircuitBuilder.diffuser_circuit(num_qubits)

        # Apply the Grover iterations
        for _ in range(iterations):
            # Apply oracle
            grover_circuit = grover_circuit.compose(oracle)
            assert isinstance(grover_circuit, QuantumCircuit)

            # Apply diffusion operator to the oracle register
            grover_circuit = grover_circuit.compose(diffusion, qubits=oracle_reg)
            assert isinstance(grover_circuit, QuantumCircuit)

        # Measure the results (only the oracle register)
        grover_circuit.measure(oracle_reg, cr)

        return grover_circuit
