package org.example;

import lombok.Getter;

import java.util.ArrayList;

import java.util.List;

public class SequenceInputOutputPair<T1, T2> {
    @Getter private List<String> sequence;
    @Getter private T1 input;
    @Getter private T2 output;
    @Getter private Object typeInput;
    @Getter private Object typeOutput;

    public SequenceInputOutputPair(List<String> sequence, T1 input, T2 output) {
        this.sequence = sequence == null ? new ArrayList<>() : sequence;
        this.input = input;
        this.output = output;

        // typeOutput: support scalar or per-step list
        if (output != null && output.getClass().isArray()) {
            Object[] arr = (Object[]) output;
            List<String> types = new ArrayList<>();
            for (Object o : arr) {
                types.add(o == null ? "null" : o.getClass().getTypeName());
            }
            this.typeOutput = types;
        } else {
            this.typeOutput = output == null ? "null" : output.getClass().getTypeName();
        }
        
        // typeInput: support flat array of args or per-step array of arrays
        if (input instanceof Object[] arr) {
            if (arr.length > 0 && arr[0] instanceof Object[]) {
                List<List<String>> perStepTypes = new ArrayList<>();
                for (Object stepObj : arr) {
                    Object[] stepArgs = (Object[]) stepObj;
                    List<String> stepTypes = new ArrayList<>();
                    for (Object arg : stepArgs) {
                        stepTypes.add(arg == null ? "null" : arg.getClass().getTypeName());
                    }
                    perStepTypes.add(stepTypes);
                }
                this.typeInput = perStepTypes;
            } else {
                String[] flatTypes = new String[arr.length];
                for (int i = 0; i < arr.length; i++) {
                    flatTypes[i] = arr[i] == null ? "null" : arr[i].getClass().getTypeName();
                }
                this.typeInput = flatTypes;
            }
        } else {
            this.typeInput = new String[]{input == null ? "null" : input.getClass().getTypeName()};
        }
    }
}