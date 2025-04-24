

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Byte input_1_0 = Byte.valueOf(args[0]);
        Byte input_2_0 = Byte.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Byte.hashCode(input_1_0);
        Integer output_2 = Byte.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == -57 && output_2 == -24) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

