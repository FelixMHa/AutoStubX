package org.example;

import lombok.Getter;

public class InputOutputPair<T1, T2> {

    @Getter
    private T1 input;

    @Getter
    private T2 output;

    @Getter
    private String[] typeInput;

    @Getter
    private String typeOutput;

    public InputOutputPair(T1 input, T2 output) {
        this.input = input;
        this.output = output;

        // set types
        typeOutput = output.getClass().getTypeName();

        // check if first is an array
        if (input.getClass().isArray()) {
            // first as array
            Object[] array = (Object[]) input;
            typeInput = new String[array.length];
            for (int i = 0; i < array.length; i++) {
                typeInput[i] = array[i].getClass().getTypeName();
            }
        } else {
            typeInput = new String[]{input.getClass().getTypeName()};
        }
    }
}
