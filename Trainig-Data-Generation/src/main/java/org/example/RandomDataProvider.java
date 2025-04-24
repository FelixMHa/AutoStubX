package org.example;

import java.util.Random;

public class RandomDataProvider {

    private static Random random = new Random();


    public static Object randomValueForType(Class<?> type) {
        // This method should be extended to handle more types as needed.
        if (type.equals(int.class) || type.equals(Integer.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;

            // get special values
            if (random.nextDouble() < 0.05) {
                int[] specialValues = {Integer.MIN_VALUE, Integer.MAX_VALUE, 0, 1, -1};
                return specialValues[random.nextInt(specialValues.length)];
            }

            // get random number from 0 to bits
            int bitsCnt = random.nextInt(Integer.SIZE - 1) + 1;

            // return random number in range
            int randomInt = random.nextInt((int) (1 << bitsCnt) - 1);

            // get random sign
            if (random.nextBoolean()) {
                randomInt = -randomInt;
            }
            return randomInt;
        } else if (type.equals(double.class) || type.equals(Double.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_decimal++;

            // get special values
            if (random.nextDouble() < 0.05) {
                double[] specialValues = {Double.MIN_VALUE, Double.MAX_VALUE, 0, 1, -1, Double.NaN, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY};
                return specialValues[random.nextInt(specialValues.length)];
            }

            // get a double with random exponent
            double randomDouble = Math.pow(2, random.nextInt(1024) - 512) * random.nextDouble();

            // get random sign
            if (random.nextBoolean()) {
                randomDouble = -randomDouble;
            }
            return randomDouble;
        } else if (type.equals(float.class) || type.equals(Float.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_decimal++;

            // get special values
            if (random.nextDouble() < 0.05) {
                float[] specialValues = {Float.MIN_VALUE, Float.MAX_VALUE, 0, 1, -1, Float.NaN, Float.POSITIVE_INFINITY, Float.NEGATIVE_INFINITY};
                return specialValues[random.nextInt(specialValues.length)];
            }

            // Generate a float with random exponent
            float randomFloat = (float) (Math.pow(2, random.nextInt(256) - 127) * random.nextFloat());

            if (random.nextBoolean()) {
                randomFloat = -randomFloat;
            }
            return randomFloat;
        } else if (type.equals(long.class) || type.equals(Long.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;

            // get special values
            if (random.nextDouble() < 0.05) {
                long[] specialValues = {Long.MIN_VALUE, Long.MAX_VALUE, 0, 1, -1};
                return specialValues[random.nextInt(specialValues.length)];
            }

            // get number of bits
            int bitsCnt = random.nextInt(63) + 1;
            long randomLong = random.nextLong() & ((1L << bitsCnt) - 1);
            if (random.nextBoolean()) {
                randomLong = -randomLong;
            }
            return randomLong;
        } else if (type.equals(short.class) || type.equals(Short.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;

            // get special values
            if (random.nextDouble() < 0.05) {
                short[] specialValues = {Short.MIN_VALUE, Short.MAX_VALUE, 0, 1, -1};
                return specialValues[random.nextInt(specialValues.length)];
            }

            // Generate a random number of bits between 1 and 15
            int bitsCnt = random.nextInt(15) + 1;

            // Generate a random short with up to bitsCnt bits
            short randomShort = (short) (random.nextInt(1 << bitsCnt) & ((1 << bitsCnt) - 1));

            // Randomly negate the number
            if (random.nextBoolean()) {
                randomShort = (short) -randomShort;
            }
            return randomShort;
        } else if (type.equals(byte.class) || type.equals(Byte.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;

            // get special values
            if (random.nextDouble() < 0.05) {
                byte[] specialValues = {Byte.MIN_VALUE, Byte.MAX_VALUE, 0, 1, -1};
                return specialValues[random.nextInt(specialValues.length)];
            }

            // Generate a random number of bits between 1 and 7
            int bitsCnt = random.nextInt(7) + 1;

            // Generate a random byte with up to bitsCnt bits
            byte randomByte = (byte) (random.nextInt(1 << bitsCnt) & ((1 << bitsCnt) - 1));

            // Randomly negate the number
            if (random.nextBoolean()) {
                randomByte = (byte) -randomByte;
            }
            return randomByte;
        } else if (type.equals(boolean.class) || type.equals(Boolean.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_boolean++;
            return random.nextBoolean();
        } else if (type.equals(char.class) || type.equals(Character.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_integer++;
            // Generate a random number of bits between 1 and 16
            int bitsCnt = random.nextInt(15) + 1;
            return (char) (random.nextInt(1 << bitsCnt));
        } else if (type.equals(String.class)) {
            GenerateTrainingDataPerClass.statistics_data_diversity_string++;
            // generate random string
            int length = random.nextInt(10);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < length; i++) {
                sb.append((char) random.nextInt(256));
            }
            return sb.toString();
        }
        throw new IllegalArgumentException("Type " + type + " not supported");
    }


}
