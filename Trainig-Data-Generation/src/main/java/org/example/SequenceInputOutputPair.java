package org.example;

import lombok.Getter;

import java.util.ArrayList;

import java.util.List;

public class SequenceInputOutputPair<T1, T2> {
    @Getter private List<String> sequence; 
    @Getter private T1 input;
    @Getter private T2 output;
    @Getter private String[] typeInput;
    @Getter private String typeOutput;

    public SequenceInputOutputPair(List<String> sequence, T1 input, T2 output) {
        this.sequence = sequence == null ? new ArrayList<>() : sequence;
        this.input = input;
        this.output = output;

        typeOutput = output == null ? "null" : output.getClass().getTypeName();
        
        if (input instanceof Object[] arr) {
            typeInput = new String[arr.length];
            for (int i = 0; i < arr.length; i++) {
                typeInput[i] = arr[i] == null ? "null" : arr[i].getClass().getTypeName();
            }
        } else {
            typeInput = new String[]{input == null ? "null" : input.getClass().getTypeName()};
        }

        
    }
}