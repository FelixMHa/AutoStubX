

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Boolean input_1_0 = Boolean.valueOf(args[0]);
        Boolean input_1_1 = Boolean.valueOf(args[1]);
        Boolean input_2_0 = Boolean.valueOf(args[2]);
        Boolean input_2_1 = Boolean.valueOf(args[3]);


        // Perform computation         
        Boolean output_1 = Boolean.logicalXor(input_1_0, input_1_1);
        Boolean output_2 = Boolean.logicalXor(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == true && output_2 == false) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

