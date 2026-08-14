package org.example;

import com.google.gson.annotations.SerializedName;
import lombok.Getter;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

public class SequenceInputOutputPair<T1, T2> {

    @Getter
    private final List<String> sequence;

    @Getter
    @SerializedName("input_args")
    private final T1 inputArgs;

    @Getter
    @SerializedName("expected_outputs")
    private final T2 expectedOutputs;

    @Getter
    @SerializedName("type_inputs")
    private final List<List<String>> typeInputs;

    @Getter
    @SerializedName("type_outputs")
    private final List<String> typeOutputs;

    @Getter
    @SerializedName("initial_state")
    private final Map<String, Object> initialState;

    @Getter
    @SerializedName("data_structure_type")
    private final String dataStructureType;

    @Getter
    @SerializedName("target_class")
    private final String targetClass;

    @Getter
    @SerializedName("receiver_refs")
    private final List<Integer> receiverRefs;

    public SequenceInputOutputPair(
            List<String> sequence,
            T1 inputArgs,
            T2 expectedOutputs,
            List<List<String>> typeInputs,
            List<String> typeOutputs,
            Map<String, Object> initialState,
            String dataStructureType,
            String targetClass) {

        this.sequence =
                sequence == null ? new ArrayList<>() : new ArrayList<>(sequence);
        this.inputArgs = inputArgs;
        this.expectedOutputs = expectedOutputs;
        this.typeInputs = new ArrayList<>(typeInputs);
        this.typeOutputs = new ArrayList<>(typeOutputs);
        this.initialState = initialState;
        this.dataStructureType = dataStructureType;
        this.targetClass = targetClass;

        // The current builder uses one persistent receiver, reference 0.
        this.receiverRefs = new ArrayList<>(
                Collections.nCopies(this.sequence.size(), 0)
        );
    }
}