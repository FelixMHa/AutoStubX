

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Byte.hashCode(input_1_0);
        Integer output_2 = Byte.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 0 && output_2 == 4) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

