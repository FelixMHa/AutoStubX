

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = input_1_0.longValue();
        Long output_2 = input_2_0.longValue();

        
        // Compare output
        if (output_1 == -10782L && output_2 == 23728964574L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

