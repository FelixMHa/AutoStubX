

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Double input_1_0 = Double.valueOf(args[0]);
        Double input_2_0 = Double.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Double.doubleToRawLongBits(input_1_0);
        Long output_2 = Double.doubleToRawLongBits(input_2_0);

        
        // Compare output
        if (output_1 == -4698833162935972480L && output_2 == -4403133870855180432L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

